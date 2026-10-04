"""Durable evidence primitives — interruption-resilience gates."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "m11_4_evidence", Path(__file__).resolve().parents[2] / "scripts/m11_4_evidence.py"
)
evidence = importlib.util.module_from_spec(SPEC)
sys.modules["m11_4_evidence"] = evidence  # dataclasses resolve their module
SPEC.loader.exec_module(evidence)


def test_atomic_json_roundtrip_and_no_temp_leftovers(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    evidence.atomic_write_json(target, {"b": 1, "a": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2, "b": 1}
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "state.json"]
    assert leftovers == []


def test_atomic_json_propagates_disk_errors(tmp_path: Path, monkeypatch) -> None:
    def failing_fsync(_fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(evidence.os, "fsync", failing_fsync)
    with pytest.raises(OSError):
        evidence.atomic_write_json(tmp_path / "state.json", {"a": 1})
    assert (
        evidence.classify_interruption(
            journal_events=["RUN_START"],
            recorded_boot_id=None,
            current_boot_id="b",
            disk_error=True,
        )
        == "INTERRUPTED_DISK"
    )


def test_journal_is_hash_chained_and_recovers_valid_prefix(tmp_path: Path) -> None:
    journal = evidence.EventJournal(tmp_path / "journal.jsonl")
    journal.append("RUN_START", {"run": "r1"})
    journal.append("CHECKPOINT", {"cycle": 1})
    journal.append("CHECKPOINT", {"cycle": 2})
    records, invalid = evidence.validate_journal(tmp_path / "journal.jsonl")
    assert invalid is None
    assert [record["seq"] for record in records] == [1, 2, 3]
    assert records[1]["previous_record_sha256"] == records[0]["record_sha256"]


def test_journal_truncated_tail_preserves_earlier_records(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = evidence.EventJournal(path)
    journal.append("RUN_START")
    journal.append("CHECKPOINT", {"cycle": 1})
    raw = path.read_bytes()
    path.write_bytes(raw[:-12])  # partially written final record
    records, invalid = evidence.validate_journal(path)
    assert [record["event"] for record in records] == ["RUN_START"]
    assert invalid == 1


def test_journal_corrupt_hash_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = evidence.EventJournal(path)
    journal.append("RUN_START")
    journal.append("CHECKPOINT")
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[1])
    tampered["payload"] = {"forged": True}
    lines[1] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    records, invalid = evidence.validate_journal(path)
    assert [record["event"] for record in records] == ["RUN_START"]
    assert invalid == 1


def test_chunks_seal_and_validate(tmp_path: Path) -> None:
    chunks = evidence.ReceiptChunks(tmp_path / "receipts", record_limit=5)
    for index in range(3):
        chunks.append({"failed": index == 2, "decoded_rate_hz": 44100}, fsync=True)
    seal = chunks.seal()
    assert seal is not None
    assert seal["record_count"] == 3
    assert seal["failed_count"] == 1
    assert chunks.validate_seals() == []
    chunks.append({"failed": False, "decoded_rate_hz": 48000}, fsync=True)
    assert chunks.validate_seals() == []


def test_chunk_seal_detects_corruption_and_count_mismatch(tmp_path: Path) -> None:
    chunks = evidence.ReceiptChunks(tmp_path / "receipts", record_limit=2)
    chunks.append({"failed": False}, fsync=True)
    chunks.append({"failed": False}, fsync=True)
    chunks.seal()
    chunk = next((tmp_path / "receipts").glob("chunk-*.jsonl"))
    chunk.write_text(chunk.read_text(encoding="utf-8") + '{"failed": false}\n')
    problems = chunks.validate_seals()
    assert any("digest mismatch" in problem for problem in problems)
    # a valid digest with a wrong declared count is also rejected
    chunk.write_text('{"failed":false}\n')
    seal_path = chunk.with_suffix(".seal.json")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    import hashlib

    seal["sha256"] = hashlib.sha256(chunk.read_bytes()).hexdigest()
    seal["record_count"] = 7
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    problems = chunks.validate_seals()
    assert any("record count mismatch" in problem for problem in problems)


def test_active_receipt_prefix_recovers_and_seals_survive(tmp_path: Path) -> None:
    chunks = evidence.ReceiptChunks(tmp_path / "receipts", record_limit=100)
    chunks.append({"failed": False, "n": 1}, fsync=True)
    chunks.append({"failed": False, "n": 2}, fsync=True)
    chunks.seal()
    chunks.append({"failed": False, "n": 3}, fsync=True)
    active = chunks.active_path()
    active.write_bytes(active.read_bytes() + b'{"failed": false, "n": 4')  # torn tail
    kept = chunks.recover_active()
    assert kept == 1
    assert chunks.validate_seals() == []
    assert [record["n"] for record in chunks.iter_records()] == [1, 2, 3]


def test_interruption_classification_from_evidence(tmp_path: Path) -> None:
    classify = evidence.classify_interruption
    assert (
        classify(
            journal_events=["RUN_START", "SIGNAL_RECEIVED"],
            recorded_boot_id="a",
            current_boot_id="a",
        )
        == "INTERRUPTED_SIGNAL"
    )
    assert (
        classify(
            journal_events=["RUN_START", "WATCHDOG_STALL"],
            recorded_boot_id="a",
            current_boot_id="a",
        )
        == "INTERRUPTED_WATCHDOG"
    )
    assert (
        classify(
            journal_events=["RUN_START"],
            recorded_boot_id="a",
            current_boot_id="b",
        )
        == "INTERRUPTED_REBOOT_OR_POWER"
    )
    assert (
        classify(
            journal_events=["RUN_START"],
            recorded_boot_id="a",
            current_boot_id="a",
        )
        == "INTERRUPTED_PROCESS_CRASH"
    )
    assert (
        classify(
            journal_events=["RUN_START", "RUN_COMPLETE"],
            recorded_boot_id="a",
            current_boot_id="a",
        )
        == "UNKNOWN_EXTERNAL_INTERRUPTION"
    )


def test_utc_wallclock_is_timezone_aware() -> None:
    stamp = evidence.utc_now_iso()
    parsed = __import__("datetime").datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None
    assert parsed.year >= 2026, "wall-clock provenance must never be epoch-based"


def test_clock_discontinuity_detection() -> None:
    assert evidence.clock_discontinuity(100.0, 10.0, 130.0, 40.0) is False
    # wall clock jumped +600 s while monotonic advanced 10 s
    assert evidence.clock_discontinuity(100.0, 10.0, 700.0, 20.0) is True


def test_evidence_module_has_no_network_dependency() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "scripts/m11_4_evidence.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import socket",
        "import urllib",
        "import requests",
        "httpx",
        "http.client",
    )
    assert not [token for token in forbidden if token in source]
