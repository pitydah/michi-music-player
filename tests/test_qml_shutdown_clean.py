"""Shutdown clean test — verifies no _pythonToCppCopy errors during shutdown."""
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_shutdown_no_python_to_cpp_copy() -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    # Preserve the ambient PYTHONPATH (CI provides gi/GStreamer bindings
    # via /usr/lib/python3/dist-packages) and prepend the repo.
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", "--qml"],
            capture_output=True,
            text=True,
            timeout=60,
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


def test_shutdown_no_traceback() -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    # Preserve the ambient PYTHONPATH (CI provides gi/GStreamer bindings
    # via /usr/lib/python3/dist-packages) and prepend the repo.
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", "--qml"],
            capture_output=True,
            text=True,
            timeout=60,
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
