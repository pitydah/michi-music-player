"""Test: CI-level integrity — compileall, ruff, and critical test paths."""
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent.parent


class TestCompileAll:
    def test_compileall_passes(self):
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q",
             "-x", ".venv/|\\.tmpl\\.", "."],
            cwd=REPO, capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"compileall failed:\n{result.stderr}"


class TestCriticalImports:
    def test_core_no_qtwidgets(self):
        code = (REPO / "michi" / "qml_app.py").read_text()
        assert "QtWidgets" not in code


class TestAppDiagnostics:
    def test_diagnostics_runs(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "main.py"), "--diagnostics"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "Python:" in result.stdout
        assert "Qt:" in result.stdout
        assert "GStreamer:" in result.stdout
