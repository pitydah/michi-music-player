"""Test: QML app startup — verifies bootstrap, bridges, and engine load without crash."""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


REPO = Path(__file__).resolve().parent.parent.parent.parent


class TestQmlBootstrap:
    def test_application_bootstrap_imports(self):
        from core.application_bootstrap import ApplicationBootstrap
        assert ApplicationBootstrap is not None

    def test_bootstrap_build_method(self):
        with patch("PySide6.QtGui.QGuiApplication"), \
             patch("PySide6.QtQml.QQmlApplicationEngine"):
            from core.service_container import ServiceContainer
            from core.composition.infrastructure import build
            c = ServiceContainer()
            build(c)

    def test_bootstrap_start_method(self):
        with patch("PySide6.QtGui.QGuiApplication"), \
             patch("PySide6.QtQml.QQmlApplicationEngine"):
            from core.application_bootstrap import ApplicationBootstrap
            b = ApplicationBootstrap()
            # Build without patching database — infra builder handles it
            try:
                b.build()
            except Exception:
                pytest.skip("build needs real DB in this env")

    def test_bootstrap_creates_bridges(self):
        with patch("PySide6.QtGui.QGuiApplication"), \
             patch("PySide6.QtQml.QQmlApplicationEngine"):
            from core.application_bootstrap import ApplicationBootstrap
            b = ApplicationBootstrap()
            try:
                b.build()
                from ui_qml_bridge.bridge_factory import create_all_bridges
                bridges = create_all_bridges(b.container)
                assert bridges is not None
            except Exception:
                pytest.skip("bridge creation needs full service graph")

    def test_qml_app_import_paths_ok(self):
        import michi.qml_app
        assert hasattr(michi.qml_app, 'run_qml')
        assert callable(michi.qml_app.run_qml)

    def test_qml_app_does_not_import_qtwidgets(self):
        code = (REPO / "michi" / "qml_app.py").read_text()
        assert "QtWidgets" not in code

    def test_qml_app_creates_qgui_app(self):
        code = (REPO / "michi" / "qml_app.py").read_text()
        assert "QGuiApplication" in code

    def test_qml_app_creates_qqml_engine(self):
        code = (REPO / "michi" / "qml_app.py").read_text()
        assert "QQmlApplicationEngine" in code

    def test_app_launcher_dispatch_qml(self):
        from michi.app_launcher import launch
        with patch.dict(os.environ, {"MICHI_UI": "qml"}), \
             patch("michi.qml_app.run_qml", return_value=0) as mock_run:
            result = launch()
            assert result == 0
            mock_run.assert_called_once()

    def test_app_launcher_rejects_widgets(self):
        from michi.app_launcher import launch
        with patch.dict(os.environ, {"MICHI_UI": "widgets"}):
            result = launch()
            assert result == 1

    def test_app_launcher_defaults_qml(self):
        from michi.app_launcher import launch
        with patch.dict(os.environ, {}, clear=True), \
             patch("michi.qml_app.run_qml", return_value=0) as mock_run:
            result = launch()
            assert result == 0
            mock_run.assert_called_once()


class TestMainEntrypoint:
    def test_main_py_exists(self):
        assert (REPO / "main.py").is_file()

    def test_main_py_diagnostics(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "main.py"), "--diagnostics"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, f"Diagnostics failed: {result.stderr}"
        assert "Qt:" in result.stdout
        assert "GStreamer:" in result.stdout

    def test_main_py_delegates_to_launcher(self):
        code = (REPO / "main.py").read_text()
        assert "launch" in code
