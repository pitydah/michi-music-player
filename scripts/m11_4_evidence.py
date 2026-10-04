"""Durable local evidence primitives for the hardened M11.4 physical campaign.

Design contract (MICHI_M11_4_HARDENED_PHYSICAL_CAMPAIGN_R11_1):

- live evidence lives under ``~/.local/state/michi/m11-4-physical`` and never
  depends on the Git worktree, the network or any agent session;
- critical files are written atomically (temp + fsync + os.replace + parent
  fsync) and the journal is an append-only hash chain;
- receipts are chunked append-only JSONL with sealed, hashed chunks so a
  sudden power loss can only damage the in-flight tail;
- recovery validates the longest valid journal prefix and the sealed chunks,
  truncates only the invalid tail of the active receipt chunk and classifies
  the interruption from evidence (never guessing "power loss").

This module is lab tooling, not product code.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import time
import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_ROOT = Path(
    os.environ.get(
        "M11_4_STATE_ROOT", str(Path.home() / ".local/state/michi/m11-4-physical")
    )
)
JOURNAL_NAME = "journal.jsonl"
RUN_META = "run-meta.json"
RUN_STATE = "run-state.json"
PROGRESS = "progress.json"
FINAL_INDEX = "final-index.json"
RECEIPTS_DIR = "receipts"
CHUNK_RECORD_LIMIT = 5000
CHECKPOINT_SECONDS = 5.0


def utc_now_iso() -> str:
    """Timezone-aware real wall clock for provenance (never from monotonic)."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def monotonic_ns() -> int:
    return time.monotonic_ns()


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def free_disk_bytes(path: Path) -> int:
    try:
        stats = os.statvfs(path)
        return stats.f_bavail * stats.f_frsize
    except OSError:
        return -1


def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def atomic_write_json(path: Path, payload: Any) -> None:
    """temp -> flush -> fsync(temp) -> os.replace -> fsync(parent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex[:8]}")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(canonical_json(payload) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fsync_directory(path.parent)


def append_jsonl_durable(path: Path, record: Any, *, fsync: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(record) + "\n")
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())


def _record_hash(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def validate_journal(path: Path) -> tuple[list[dict[str, Any]], int | None]:
    """Longest valid hash-chain prefix; index of the first invalid line."""
    if not path.exists():
        return [], None
    good: list[dict[str, Any]] = []
    previous = ""
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return good, index
        if not isinstance(record, dict):
            return good, index
        if record.get("previous_record_sha256") != previous:
            return good, index
        if _record_hash(record) != record.get("record_sha256"):
            return good, index
        previous = str(record.get("record_sha256"))
        good.append(record)
    return good, None


class EventJournal:
    """Append-only, fsynced, hash-chained event journal."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records, _ = validate_journal(path)
        self._seq = int(records[-1]["seq"]) if records else 0
        self._last_hash = str(records[-1]["record_sha256"]) if records else ""
        self._boot = boot_id()

    def append(self, event: str, payload: Any = None, *, fsync: bool = True) -> dict:
        self._seq += 1
        record = {
            "seq": self._seq,
            "event": event,
            "wall_time_utc": utc_now_iso(),
            "monotonic_ns": monotonic_ns(),
            "boot_id": self._boot,
            "pid": os.getpid(),
            "payload": payload,
            "previous_record_sha256": self._last_hash,
        }
        record["record_sha256"] = _record_hash(record)
        append_jsonl_durable(self.path, record, fsync=fsync)
        self._last_hash = record["record_sha256"]
        return record


def seal_payload(path: Path, record_count: int, failed_count: int) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return {
        "file": path.name,
        "size": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "record_count": record_count,
        "failed_count": failed_count,
    }


class ReceiptChunks:
    """Chunked append-only receipt storage with sealed, hashed chunks."""

    def __init__(self, directory: Path, *, record_limit: int = CHUNK_RECORD_LIMIT):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.record_limit = record_limit
        self._count = 0
        self._failed = 0
        self._last_flush = time.monotonic()

    def _chunk_paths(self) -> Iterator[tuple[Path, Path]]:
        for chunk in sorted(self.directory.glob("chunk-*.jsonl")):
            yield chunk, chunk.with_suffix(".seal.json")

    def _next_index(self) -> int:
        highest = 0
        for chunk, _ in self._chunk_paths():
            try:
                highest = max(highest, int(chunk.stem.split("-")[1]))
            except (IndexError, ValueError):
                continue
        return highest + 1

    def active_path(self) -> Path:
        return self.directory / "active.jsonl"

    def append(self, record: dict[str, Any], *, fsync: bool = False) -> None:
        active = self.active_path()
        append_jsonl_durable(active, record, fsync=fsync)
        self._count += 1
        if record.get("failed") is True:
            self._failed += 1
        now = time.monotonic()
        if self._count >= self.record_limit or (now - self._last_flush) >= 30.0:
            self.seal()
        self._last_flush = now

    def flush(self) -> None:
        active = self.active_path()
        if active.exists():
            with active.open("rb") as handle:
                os.fsync(handle.fileno())

    def seal(self) -> dict[str, Any] | None:
        active = self.active_path()
        if not active.exists() or self._count == 0:
            return None
        index = self._next_index()
        chunk = self.directory / f"chunk-{index:06d}.jsonl"
        os.replace(active, chunk)
        fsync_directory(self.directory)
        seal = seal_payload(chunk, self._count, self._failed)
        atomic_write_json(chunk.with_suffix(".seal.json"), seal)
        self._count = 0
        self._failed = 0
        return seal

    def recover_active(self) -> int:
        """Truncate only the invalid tail of the ACTIVE chunk. Returns kept lines.

        Sealed chunks and historical records are never rewritten.
        """
        active = self.active_path()
        if not active.exists():
            return 0
        raw = active.read_bytes()
        offset = 0
        good = 0
        for line in raw.splitlines(keepends=True):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                break
            if not isinstance(record, dict):
                break
            offset += len(line)
            good += 1
        if offset != len(raw):
            with active.open("r+b") as handle:
                handle.truncate(offset)
                handle.flush()
                os.fsync(handle.fileno())
        self._count = good
        return good

    def iter_records(self) -> Iterator[dict[str, Any]]:
        for chunk, _ in self._chunk_paths():
            for line in chunk.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)
        active = self.active_path()
        if active.exists():
            for line in active.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    def validate_seals(self) -> list[str]:
        """Return a list of seal violations (empty means every seal is valid)."""
        problems: list[str] = []
        for chunk, seal_path in self._chunk_paths():
            if not seal_path.exists():
                problems.append(f"{chunk.name}: missing seal")
                continue
            try:
                seal = json.loads(seal_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                problems.append(f"{chunk.name}: unreadable seal")
                continue
            digest = hashlib.sha256(chunk.read_bytes()).hexdigest()
            if seal.get("sha256") != digest:
                problems.append(f"{chunk.name}: seal digest mismatch")
                continue
            count = 0
            failed = 0
            for line in chunk.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                count += 1
                if record.get("failed") is True:
                    failed += 1
            if seal.get("record_count") != count:
                problems.append(f"{chunk.name}: seal record count mismatch")
            if seal.get("failed_count") != failed:
                problems.append(f"{chunk.name}: seal failed count mismatch")
        return problems


@dataclass(frozen=True)
class RunLayout:
    root: Path
    journal_path: Path
    receipts_dir: Path

    @classmethod
    def create(cls, campaign_id: str, run_id: str) -> RunLayout:
        root = STATE_ROOT / campaign_id / run_id
        for name in (
            "checkpoints",
            "receipts",
            "kernel",
            "diagnostics",
            "resource-checkpoints",
            "usb-checkpoints",
        ):
            (root / name).mkdir(parents=True, exist_ok=True)
        fsync_directory(root)
        return cls(
            root=root,
            journal_path=root / JOURNAL_NAME,
            receipts_dir=root / RECEIPTS_DIR,
        )

    def write_meta(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.root / RUN_META, payload)

    def write_state(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.root / RUN_STATE, payload)

    def write_progress(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.root / PROGRESS, payload)


def classify_interruption(
    *,
    journal_events: Iterable[str],
    recorded_boot_id: str | None,
    current_boot_id: str,
    watchdog_stalled: bool = False,
    disk_error: bool = False,
    device_error: bool = False,
) -> str:
    """Honest interruption classification from evidence, never guessed."""
    events = list(journal_events)
    if disk_error or "DISK_ERROR" in events:
        return "INTERRUPTED_DISK"
    if device_error or "DEVICE_ERROR" in events:
        return "INTERRUPTED_DEVICE"
    if watchdog_stalled or "WATCHDOG_STALL" in events:
        return "INTERRUPTED_WATCHDOG"
    if "SIGNAL_RECEIVED" in events:
        return "INTERRUPTED_SIGNAL"
    if recorded_boot_id and recorded_boot_id != current_boot_id:
        return "INTERRUPTED_REBOOT_OR_POWER"
    if "RUN_START" in events and "RUN_COMPLETE" not in events:
        return "INTERRUPTED_PROCESS_CRASH"
    return "UNKNOWN_EXTERNAL_INTERRUPTION"


def clock_discontinuity(
    previous_wall_s: float,
    previous_mono_s: float,
    wall_s: float,
    mono_s: float,
    *,
    tolerance_s: float = 5.0,
) -> bool:
    """True when wall-clock and monotonic deltas disagree materially."""
    wall_delta = wall_s - previous_wall_s
    mono_delta = mono_s - previous_mono_s
    return abs(wall_delta - mono_delta) > tolerance_s


def install_signal_handlers(
    journal: EventJournal, on_event: Callable[[str], None] | None = None
) -> None:
    """Record SIGNAL_RECEIVED + RUN_INTERRUPTED and fsync before exiting."""

    def handler(signum, _frame) -> None:
        name = signal.Signals(signum).name
        try:
            journal.append("SIGNAL_RECEIVED", {"signal": name})
            journal.append("RUN_INTERRUPTED", {"signal": name})
        finally:
            if on_event is not None:
                on_event(name)
            raise SystemExit(128 + signum)

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, handler)
