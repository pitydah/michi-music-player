from __future__ import annotations
"""Tests for separated launchers — qml_app, widgets_app, app_launcher."""

import ast
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestQmlAppLauncher:
    def test_qml_app_does_not_import_qt_widgets(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        lines = source.splitlines()
        import_lines = [ln for ln in lines if ln.strip().startswith("import") or ln.strip().startswith("from")]
        assert not any("QtWidgets" in ln for ln in import_lines), "qml_app must not import QtWidgets"

    def test_qml_app_does_not_import_ui(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "from ui." not in source, "qml_app must not import ui.* modules"
        assert "import ui." not in source, "qml_app must not import ui.* modules"

    def test_qml_app_imports_qgui_app_and_qqml_engine(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "QGuiApplication" in source
        assert "QQmlApplicationEngine" in source

    def test_qml_app_run_returns_exit_code(self):
        import michi.qml_app
        with (
            patch("PySide6.QtGui.QGuiApplication") as MockApp,
            patch("PySide6.QtQml.QQmlApplicationEngine") as MockEngine,
            patch("core.application_bootstrap.ApplicationBootstrap") as MockBootstrap,
        ):
            mock_app = MagicMock()
            mock_app.exec.return_value = 0
            MockApp.instance.return_value = None
            MockApp.return_value = mock_app
            mock_engine = MagicMock()
            mock_engine.rootObjects.return_value = [MagicMock()]
            MockEngine.return_value = mock_engine
            code = michi.qml_app.run_qml()
            assert code == 0
            MockBootstrap.return_value.run.assert_called_once_with(mock_engine)


class TestWidgetsAppLauncher:
    def test_widgets_app_does_not_create_qml_objects(self):
        import michi.widgets_app
        source = Path(michi.widgets_app.__file__).read_text()
        assert "QQmlApplicationEngine" not in source
        assert "QGuiApplication" not in source

    def test_widgets_app_imports_qapplication(self):
        import michi.widgets_app
        source = Path(michi.widgets_app.__file__).read_text()
        assert "QApplication" in source

    def test_widgets_app_remains_source_compatible(self):
        from michi.widgets_app import run_widgets
        assert callable(run_widgets)

    def test_widgets_app_returns_1_on_import_error(self):
        import michi.widgets_app
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            code = michi.widgets_app.run_widgets()
            assert code == 1


class TestAppLauncher:
    def test_app_launcher_does_not_create_qapplication_directly(self):
        import michi.app_launcher
        source = Path(michi.app_launcher.__file__).read_text()
        tree = ast.parse(source)
        assert not any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            and "PySide6" in ast.unparse(node)
            for node in ast.walk(tree)
        )

    def test_app_launcher_defaults_to_qml(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("michi.qml_app.run_qml") as mock_run,
        ):
            mock_run.return_value = 0
            assert michi.app_launcher.launch() == 0
            mock_run.assert_called_once()

    def test_app_launcher_qml_mode_dispatches_to_qml(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {"MICHI_UI": "qml"}, clear=True),
            patch("michi.qml_app.run_qml") as mock_run,
        ):
            mock_run.return_value = 0
            assert michi.app_launcher.launch() == 0
            mock_run.assert_called_once()

    def test_app_launcher_verify_mode(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {"MICHI_UI": "verify"}, clear=True),
            patch("michi.verify_app.run_verify") as mock_run,
        ):
            mock_run.return_value = 0
            assert michi.app_launcher.launch() == 0
            mock_run.assert_called_once()

    def test_michi_entrypoint_exists(self):
        from michi.app_launcher import launch
        assert callable(launch)

    def test_michi_qml_entrypoint_exists(self):
        from michi.qml_app import run_qml
        assert callable(run_qml)

    def test_widgets_entrypoint_exists(self):
        from michi.widgets_app import run_widgets
        assert callable(run_widgets)
