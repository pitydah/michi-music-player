from __future__ import annotations
"""Tests for HC — Launchers definitivos.
Verifies qml_app, widgets_app, app_launcher, verify_app contracts."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestQmlAppNoWidgets:
    def test_qml_app_does_not_import_qt_widgets(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        lines = source.splitlines()
        import_lines = [ln for ln in lines if ln.strip().startswith("import") or ln.strip().startswith("from")]
        assert not any("QtWidgets" in ln for ln in import_lines), "qml_app must not import QtWidgets"

    def test_qml_app_does_not_import_ui_window(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "from ui.window" not in source
        assert "import legacy_widgets.ui.old_window.window" not in source

    def test_qml_app_does_not_import_ui_dialogs(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "from ui.dialogs" not in source
        assert "import ui.dialogs" not in source

    def test_qml_app_does_not_import_ui_pages(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "from ui.pages" not in source
        assert "import ui.pages" not in source

    def test_qml_app_does_not_import_ui_any(self):
        import michi.qml_app
        source = Path(michi.qml_app.__file__).read_text()
        assert "import ui." not in source
        assert "from ui." not in source


class TestWidgetsAppConsumesCore:
    def test_widgets_app_imports_application_bootstrap(self):
        import michi.widgets_app
        source = Path(michi.widgets_app.__file__).read_text()
        assert "ApplicationBootstrap" in source

    def test_widgets_app_invokes_bootstrap_build_and_start(self):
        import michi.widgets_app
        source = Path(michi.widgets_app.__file__).read_text()
        assert ".build()" in source
        assert ".start()" in source

    def test_widgets_app_imports_qapplication(self):
        import michi.widgets_app
        source = Path(michi.widgets_app.__file__).read_text()
        assert "QApplication" in source

    def test_widgets_app_run_returns_exit_code(self):
        import michi.widgets_app
        boot_patch = patch("core.application_bootstrap.ApplicationBootstrap")
        with boot_patch as MockBoot:
            mock_boot = MagicMock()
            MockBoot.return_value = mock_boot
            with patch("PySide6.QtWidgets.QApplication") as MockApp:
                mock_app = MagicMock()
                mock_app.exec.return_value = 0
                MockApp.return_value = mock_app
                with patch.dict("sys.modules", {"main": MagicMock(MainWindow=MagicMock())}):
                    code = michi.widgets_app.run_widgets()
                    assert code == 0
                    mock_boot.build.assert_called_once()
                    mock_boot.start.assert_called_once()


class TestAppLauncherNoQt:
    def test_app_launcher_does_not_create_qapplication(self):
        import michi.app_launcher
        source = Path(michi.app_launcher.__file__).read_text()
        assert "QApplication" not in source
        assert "QGuiApplication" not in source
        assert "QQmlApplicationEngine" not in source

    def test_app_launcher_defaults_to_widgets(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("michi.app_launcher.sys.exit"),
            patch("michi.widgets_app.run_widgets") as mock_run,
        ):
            mock_run.return_value = 0
            michi.app_launcher.launch()
            mock_run.assert_called_once()

    def test_app_launcher_qml_mode_dispatches_to_qml(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {"MICHI_UI": "qml"}, clear=True),
            patch("michi.app_launcher.sys.exit"),
            patch("michi.qml_app.run_qml") as mock_run,
        ):
            mock_run.return_value = 0
            michi.app_launcher.launch()
            mock_run.assert_called_once()

    def test_app_launcher_verify_mode_dispatches_to_verify(self):
        import michi.app_launcher
        with (
            patch.dict(os.environ, {"MICHI_UI": "verify"}, clear=True),
            patch("michi.app_launcher.sys.exit"),
            patch("michi.verify_app.run_verify") as mock_run,
        ):
            mock_run.return_value = 0
            michi.app_launcher.launch()
            mock_run.assert_called_once()


class TestVerifyApp:
    def test_verify_app_has_run_verify(self):
        from michi.verify_app import run_verify
        assert callable(run_verify)

    def test_verify_app_sets_safe_mode(self):
        import michi.verify_app
        source = Path(michi.verify_app.__file__).read_text()
        assert "MICHI_SAFE_MODE" in source
        assert "offscreen" in source

    def test_verify_app_returns_1_on_failure(self):
        import michi.verify_app
        with patch("core.application_bootstrap.ApplicationBootstrap") as MockBoot:
            mock_boot = MagicMock()
            mock_boot.build.side_effect = Exception("fail")
            MockBoot.return_value = mock_boot
            code = michi.verify_app.run_verify()
            assert code == 1


class TestEntrypoints:
    def test_michi_entrypoint_exists(self):
        from michi.app_launcher import launch
        assert callable(launch)

    def test_michi_qml_entrypoint_exists(self):
        from michi.qml_app import run_qml
        assert callable(run_qml)

    def test_michi_widgets_entrypoint_exists(self):
        from michi.widgets_app import run_widgets
        assert callable(run_widgets)

    def test_michi_qml_verify_entrypoint_exists(self):
        from michi.verify_app import run_verify
        assert callable(run_verify)

    def test_pyproject_has_all_entrypoints(self):
        import tomllib
        path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        data = tomllib.loads(path.read_text())
        scripts = data["project"]["scripts"]
        assert "michi" in scripts
        assert "michi-qml" in scripts
        assert "michi-widgets" in scripts
        assert "michi-qml-verify" in scripts


class TestMainPyNoAuto:
    def test_main_py_no_michi_ui_auto(self):
        path = Path(__file__).resolve().parent.parent.parent / "main.py"
        source = path.read_text()
        assert "MICHI_UI=auto" not in source
        assert "_resolve_ui_mode" not in source

    def test_main_py_no_try_qml(self):
        path = Path(__file__).resolve().parent.parent.parent / "main.py"
        source = path.read_text()
        assert "_try_qml" not in source
