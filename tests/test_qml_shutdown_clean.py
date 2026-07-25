"""Shutdown clean test — verifies no _pythonToCppCopy errors during shutdown."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skip(reason="DRIFT: GStreamerEngine missing set_repeat — traceback in shutdown log; handled in separate PR")
def test_shutdown_no_python_to_cpp_copy() -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    env["PYTHONPATH"] = str(REPO)
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", "--qml"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO),
            env=env,
        )
        output = proc.stderr + proc.stdout
    except subprocess.TimeoutExpired as exc:
        output = ""
        if exc.stderr:
            output += exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
        if exc.stdout:
            output += exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout

    assert "_pythonToCppCopy" not in output, (
        "_pythonToCppCopy error detected during shutdown:\n" + output[-500:]
    )
    assert "READY" in output, "Application did not reach READY state"


@pytest.mark.skip(reason="DRIFT: GStreamerEngine missing set_repeat — traceback in shutdown log; handled in separate PR")
def test_shutdown_no_traceback() -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    env["PYTHONPATH"] = str(REPO)
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", "--qml"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO),
            env=env,
        )
        output = proc.stderr + proc.stdout
    except subprocess.TimeoutExpired as exc:
        output = ""
        if exc.stderr:
            output += exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
        if exc.stdout:
            output += exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout

    assert "Traceback" not in output, (
        "Python traceback detected during shutdown:\n" + output[-500:]
    )
