"""Test that the app starts without bootstrap errors."""
import os
import signal
import sys
import pytest
import subprocess


@pytest.mark.skipif(not os.environ.get('CI'), reason="Requires full CI environment")
def test_app_starts():
    """python main.py --qml starts and reaches READY state."""
    proc = subprocess.Popen(
        [sys.executable, "main.py", "--qml"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        # App is still running (healthy) — kill and check for READY
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
    assert "READY" in stdout, f"App did not reach READY: {stderr[-500:]}"
    assert "Traceback" not in stderr, f"App crashed: {stderr[-500:]}"


@pytest.mark.skipif(not os.environ.get('CI'), reason="Requires full CI environment")
def test_app_no_duplicate_actions():
    """No duplicate action IDs registered."""
    proc = subprocess.Popen(
        [sys.executable, "main.py", "--qml"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
    assert "Duplicate" not in stderr, f"Duplicate actions: {stderr[-500:]}"
