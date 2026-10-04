"""External supervisor — completion, watchdog, signal and recovery gates."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SUPERVISOR = (
    Path(__file__).resolve().parents[2] / "scripts/m11_4_physical_supervisor.py"
)

CHILD_HEARTBEAT = (
    "import json, os, time\n"
    "from pathlib import Path\n"
    "run = Path(os.environ['M11_4_RUN_DIR'])\n"
    "for index in range(30):\n"
    "    tmp = run / 'progress.json.tmp'\n"
    "    payload = {'monotonic_ns': time.monotonic_ns(), 'seq': index}\n"
    "    tmp.write_text(json.dumps(payload))\n"
    "    os.replace(tmp, run / 'progress.json')\n"
    "    time.sleep(0.2)\n"
)


def _supervisor_run(
    state_root: Path,
    *,
    campaign: str = "camp",
    experiment: str = "smoke",
    child_code: str,
    watchdog: float = 120.0,
    grace: float = 2.0,
    run_id: str | None = None,
) -> subprocess.CompletedProcess:
    env = dict(os.environ, M11_4_STATE_ROOT=str(state_root))
    argv = [
        sys.executable,
        str(SUPERVISOR),
        "run",
        "--campaign-id",
        campaign,
        "--experiment",
        experiment,
        "--watchdog-seconds",
        str(watchdog),
        "--kill-grace-seconds",
        str(grace),
    ]
    if run_id:
        argv += ["--run-id", run_id]
    argv += ["--", sys.executable, "-c", child_code]
    return subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)


def _summary(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_supervisor_clean_completion_finalizes(tmp_path: Path) -> None:
    result = _supervisor_run(tmp_path, child_code=CHILD_HEARTBEAT)
    assert result.returncode == 0, result.stderr
    payload = _summary(result)
    assert payload["classification"] == "COMPLETE"
    run_dir = Path(payload["run_dir"])
    assert (run_dir / "final-index.json").exists()
    assert (run_dir / "run-state.json").exists()
    journal = (run_dir / "journal.jsonl").read_text(encoding="utf-8")
    for event in ("RUN_START", "CHILD_STARTED", "RUN_COMPLETE", "FINALIZE"):
        assert event in journal
    index = json.loads((run_dir / "final-index.json").read_text(encoding="utf-8"))
    assert index["seal_problems"] == []
    assert index["artifacts"]


def test_supervisor_child_failure_is_not_complete(tmp_path: Path) -> None:
    result = _supervisor_run(tmp_path, child_code="import sys; sys.exit(3)")
    assert result.returncode == 1
    payload = _summary(result)
    assert payload["exit_code"] == 3
    assert payload["classification"] == "CHILD_NONZERO_EXIT"


def test_supervisor_watchdog_stall_captures_and_kills(tmp_path: Path) -> None:
    result = _supervisor_run(
        tmp_path, child_code="import time; time.sleep(120)", watchdog=3.0
    )
    assert result.returncode == 2, result.stderr
    payload = _summary(result)
    assert payload["classification"] == "INTERRUPTED_WATCHDOG"
    assert payload["stalled"] is True
    run_dir = Path(payload["run_dir"])
    assert (run_dir / "diagnostics" / "proc.txt").exists()
    assert (run_dir / "diagnostics" / "process-tree.txt").exists()
    assert "WATCHDOG_STALL" in (run_dir / "journal.jsonl").read_text(encoding="utf-8")


def test_supervisor_sigterm_records_signal_stops_child_and_recovers(
    tmp_path: Path,
) -> None:
    env = dict(os.environ, M11_4_STATE_ROOT=str(tmp_path))
    process = subprocess.Popen(
        [
            sys.executable,
            str(SUPERVISOR),
            "run",
            "--campaign-id",
            "camp",
            "--experiment",
            "smoke",
            "--run-id",
            "fixed-run",
            "--watchdog-seconds",
            "120",
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(120)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    journal_path = tmp_path / "camp" / "fixed-run" / "journal.jsonl"
    deadline = time.monotonic() + 30
    child_pid = None
    while time.monotonic() < deadline:
        if journal_path.exists():
            lines = journal_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if "CHILD_STARTED" in line:
                    child_pid = json.loads(line)["payload"]["pid"]
            if child_pid is not None:
                break
        time.sleep(0.1)
    assert child_pid is not None, "child never started"

    process.send_signal(signal.SIGTERM)
    process.wait(timeout=30)
    assert process.returncode != 0
    text = journal_path.read_text(encoding="utf-8")
    assert "SIGNAL_RECEIVED" in text
    with pytest.raises(OSError):
        os.kill(child_pid, 0)

    recovered = subprocess.run(
        [
            sys.executable,
            str(SUPERVISOR),
            "recover",
            "--campaign-id",
            "camp",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads(recovered.stdout)
    assert payload["runs"], payload
    entry = next(run for run in payload["runs"] if run["run_id"] == "fixed-run")
    assert entry["classification"] == "INTERRUPTED_SIGNAL"
    assert entry["duration_is_partial"] is True


def test_supervisor_runs_are_separate_and_never_concatenated(tmp_path: Path) -> None:
    first = _supervisor_run(tmp_path, child_code=CHILD_HEARTBEAT, run_id="attempt-a")
    second = _supervisor_run(tmp_path, child_code=CHILD_HEARTBEAT, run_id="attempt-b")
    a = Path(_summary(first)["run_dir"])
    b = Path(_summary(second)["run_dir"])
    assert a != b
    assert (a / "run-meta.json").exists() and (b / "run-meta.json").exists()


def test_supervisor_has_no_network_dependency() -> None:
    source = SUPERVISOR.read_text(encoding="utf-8")
    forbidden = (
        "import socket",
        "import urllib",
        "import requests",
        "httpx",
        "http.client",
    )
    assert not [token for token in forbidden if token in source]
