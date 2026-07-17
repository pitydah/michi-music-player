"""Test that the app starts without bootstrap errors."""
import os
import sys
import pytest
import subprocess


@pytest.mark.skipif(not os.environ.get('CI'), reason="Requires full CI environment")
def test_app_starts():
    """python main.py --qml completes without errors."""
    result = subprocess.run(
        [sys.executable, "main.py", "--qml"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    assert "READY" in result.stdout, f"App did not start: {result.stderr[-500:]}"
    assert "Traceback" not in result.stderr, f"App crashed: {result.stderr[-500:]}"


@pytest.mark.skipif(not os.environ.get('CI'), reason="Requires full CI environment")
def test_app_no_duplicate_actions():
    """No duplicate action IDs registered."""
    result = subprocess.run(
        [sys.executable, "main.py", "--qml"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    assert "Duplicate" not in result.stderr, f"Duplicate actions: {result.stderr[-500:]}"
