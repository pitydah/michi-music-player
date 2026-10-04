"""External supervisor for hardened M11.4 physical runs.

The risky Michi/GStreamer process always executes as a CHILD of this
supervisor, so an in-process wedge (for example a permanent
``gst_element_change_state`` C-level wait) cannot prevent the watchdog,
diagnostic capture and honest interruption classification.

The child is expected to write durable progress into the run directory
(``M11_4_RUN_DIR`` in its environment) using ``scripts/m11_4_evidence.py``:
a ``progress.json`` heartbeat and, for lab runs, chunked receipts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "m11_4_evidence", ROOT / "scripts/m11_4_evidence.py"
)
evidence = importlib.util.module_from_spec(_spec)
sys.modules["m11_4_evidence"] = evidence
_spec.loader.exec_module(evidence)

DIAGNOSTIC_TIMEOUT_S = 5.0


def _capture(command: list[str], *, timeout: float = DIAGNOSTIC_TIMEOUT_S) -> str:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
        return completed.stdout or completed.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"<diagnostic unavailable: {type(exc).__name__}: {exc}>"


def _process_tree(pid: int) -> str:
    return _capture(["ps", "-eo", "pid,ppid,stat,etime,cmd"])


def _proc_snapshot(pid: int, name: str) -> str:
    base = Path(f"/proc/{pid}")
    if not base.exists():
        return "<process gone>"
    parts = [
        f"== {name} status ==",
        (base / "status").read_text(errors="replace")
        if (base / "status").exists()
        else "",
        f"== {name} threads ==",
    ]
    for task in sorted((base / "task").glob("*")):
        try:
            comm = (task / "comm").read_text().strip()
            wchan = (task / "wchan").read_text().strip()
        except OSError:
            continue
        parts.append(f"{task.name} {comm} {wchan}")
    parts.append(f"== {name} fds ==")
    try:
        for fd in sorted((base / "fd").iterdir()):
            try:
                parts.append(f"{fd.name} -> {os.readlink(fd)}")
            except OSError:
                continue
    except OSError:
        parts.append("<fd listing unavailable>")
    return "\n".join(parts) + "\n"


def _capture_diagnostics(run_dir: Path, pid: int) -> None:
    diagnostics = run_dir / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    payloads = {
        "process-tree.txt": _process_tree(pid),
        "proc.txt": _proc_snapshot(pid, "child"),
        "alsa-holders.txt": _capture(["fuser", "-v", "/dev/snd/pcmC3D0p"]),
        "usb-sysfs.txt": _capture(
            ["find", "/sys/bus/usb/devices/3-3.3.2", "-maxdepth", "1"]
        ),
        "kernel-journal.txt": _capture(
            ["journalctl", "--dmesg", "--no-pager", "--output=cat", "-n", "200"]
        ),
    }
    for name, content in payloads.items():
        path = diagnostics / name
        with path.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    evidence.fsync_directory(diagnostics)


def _terminate(child: subprocess.Popen, grace_s: float) -> None:
    try:
        child.terminate()
    except OSError:
        return
    try:
        child.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        try:
            child.kill()
        except OSError:
            return
        child.wait()


def _finalize(run_dir: Path, journal) -> dict:
    layout = evidence.RunLayout(
        root=run_dir,
        journal_path=run_dir / evidence.JOURNAL_NAME,
        receipts_dir=run_dir / evidence.RECEIPTS_DIR,
    )
    receipts = evidence.ReceiptChunks(layout.receipts_dir)
    receipts.recover_active()
    seal_problems = receipts.validate_seals()
    records, invalid = evidence.validate_journal(layout.journal_path)
    index: dict[str, dict] = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != evidence.FINAL_INDEX:
            import hashlib

            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            index[str(path.relative_to(run_dir))] = {
                "size": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
    evidence.atomic_write_json(
        run_dir / evidence.FINAL_INDEX,
        {
            "journal_records": len(records),
            "journal_first_invalid_line": invalid,
            "seal_problems": seal_problems,
            "artifacts": index,
        },
    )
    return {"journal_records": len(records), "seal_problems": seal_problems}


def _scan_unfinished(campaign_id: str) -> list[dict]:
    """Classify unfinished runs of a campaign from durable evidence only."""
    reports: list[dict] = []
    base = evidence.STATE_ROOT / campaign_id
    if not base.exists():
        return reports
    current_boot = evidence.boot_id()
    for run_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        state_path = run_dir / evidence.RUN_STATE
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("state") in ("COMPLETE", "FINALIZED", "INTERRUPTED_WATCHDOG"):
                continue
        records, _ = evidence.validate_journal(run_dir / evidence.JOURNAL_NAME)
        events = [record["event"] for record in records]
        if not events:
            continue
        recorded_boot = records[0].get("boot_id")
        classification = evidence.classify_interruption(
            journal_events=events,
            recorded_boot_id=recorded_boot,
            current_boot_id=current_boot,
        )
        reports.append(
            {
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "events": len(events),
                "classification": classification,
                "duration_is_partial": True,
            }
        )
    return reports


def _run(args: argparse.Namespace) -> int:
    campaign_id = args.campaign_id
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    child_command = list(args.child)
    if child_command and child_command[0] == "--":
        child_command = child_command[1:]
    if not child_command:
        raise SystemExit("run requires a child command after --")
    layout = evidence.RunLayout.create(campaign_id, run_id)
    journal = evidence.EventJournal(layout.journal_path)
    meta = (
        json.loads(Path(args.meta_json).read_text(encoding="utf-8"))
        if args.meta_json
        else {}
    )
    meta.update(
        {
            "campaign_id": campaign_id,
            "run_id": run_id,
            "experiment": args.experiment,
            "supervisor_pid": os.getpid(),
            "boot_id": evidence.boot_id(),
            "started_wallclock_utc": evidence.utc_now_iso(),
            "started_monotonic_ns": evidence.monotonic_ns(),
            "watchdog_seconds": args.watchdog_seconds,
            "free_disk_bytes": evidence.free_disk_bytes(layout.root),
        }
    )
    layout.write_meta(meta)
    journal.append(
        "RUN_START", {"experiment": args.experiment, "command": child_command}
    )
    evidence.install_signal_handlers(journal)

    stdout_path = layout.root / "stdout.log"
    stderr_path = layout.root / "stderr.log"
    env = dict(os.environ)
    env["M11_4_RUN_DIR"] = str(layout.root)
    with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
        child = subprocess.Popen(child_command, stdout=out, stderr=err, env=env)
        try:
            journal.append("CHILD_STARTED", {"pid": child.pid})
            progress_path = layout.root / evidence.PROGRESS
            last_progress_at = time.monotonic()
            last_progress_value = None
            stalled = False
            while child.poll() is None:
                time.sleep(1.0)
                current = None
                if progress_path.exists():
                    try:
                        current = json.loads(
                            progress_path.read_text(encoding="utf-8")
                        ).get("monotonic_ns")
                    except (OSError, json.JSONDecodeError):
                        current = None
                if current is not None and current != last_progress_value:
                    last_progress_value = current
                    last_progress_at = time.monotonic()
                if time.monotonic() - last_progress_at > args.watchdog_seconds:
                    stalled = True
                    journal.append(
                        "WATCHDOG_STALL",
                        {
                            "quiet_seconds": round(
                                time.monotonic() - last_progress_at, 1
                            )
                        },
                    )
                    _capture_diagnostics(layout.root, child.pid)
                    _terminate(child, args.kill_grace_seconds)
                    break
            exit_code = child.wait()
        finally:
            if child.poll() is None:
                _terminate(child, args.kill_grace_seconds)

    layout.write_state(
        {
            "state": "CHILD_EXITED",
            "exit_code": exit_code,
            "stalled": stalled,
            "finished_wallclock_utc": evidence.utc_now_iso(),
        }
    )
    if stalled:
        journal.append("RUN_INTERRUPTED", {"classification": "INTERRUPTED_WATCHDOG"})
        classification = "INTERRUPTED_WATCHDOG"
    elif exit_code == 0:
        journal.append("RUN_COMPLETE", {})
        classification = "COMPLETE"
    else:
        # A deliberate non-zero child exit is not an external interruption:
        # the child ran to completion and reported failure. Interruption
        # classification stays reserved for runs that vanish (recovery scan).
        classification = "CHILD_NONZERO_EXIT"
        journal.append("CHILD_FAILED", {"exit_code": exit_code})
    summary = _finalize(layout.root, journal)
    journal.append("FINALIZE", summary)
    result = {
        "run_id": run_id,
        "run_dir": str(layout.root),
        "classification": classification,
        "exit_code": exit_code,
        "stalled": stalled,
        **summary,
    }
    layout.write_state({"state": classification, **result})
    print(json.dumps(result, sort_keys=True))
    if classification == "COMPLETE" and exit_code == 0:
        return 0
    if classification == "INTERRUPTED_WATCHDOG":
        return 2
    return 1


def _status(args: argparse.Namespace) -> int:
    runs = _scan_unfinished(args.campaign_id)
    if args.run_id:
        runs = [run for run in runs if run["run_id"] == args.run_id]
    print(json.dumps({"campaign_id": args.campaign_id, "runs": runs}, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m11-4-physical-supervisor")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--campaign-id", required=True)
    run.add_argument("--experiment", required=True)
    run.add_argument("--run-id", default=None)
    run.add_argument("--watchdog-seconds", type=float, default=120.0)
    run.add_argument("--kill-grace-seconds", type=float, default=10.0)
    run.add_argument("--meta-json", default=None)
    run.add_argument("child", nargs=argparse.REMAINDER)

    status = sub.add_parser("status")
    status.add_argument("--campaign-id", required=True)
    status.add_argument("--run-id", default=None)

    recover = sub.add_parser("recover")
    recover.add_argument("--campaign-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "run":
        if not args.child:
            parser.error("run requires a child command after --")
        return _run(args)
    if args.command == "status":
        return _status(args)
    if args.command == "recover":
        args.run_id = None
        return _status(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
