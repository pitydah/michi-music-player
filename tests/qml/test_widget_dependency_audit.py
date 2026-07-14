"""Test widget dependency audit script."""
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "qml_widget_dependency_audit.py"


def test_script_runs():
    result = subprocess.run([sys.executable, str(SCRIPT_PATH)], capture_output=True, text=True)
    assert result.returncode in (0, 1)
    assert "QML Widget Dependency Audit" in result.stdout
