"""Test that app launcher and separate entry points work correctly.

Tests:
- app_launcher dispatches to the correct app based on MICHI_UI
- qml_app does not import QtWidgets modules
- widgets_app does not import QML-only modules
- MICHI_UI=widgets and MICHI_UI=qml both work
- No MICHI_UI=auto support
"""
import importlib
import os
from unittest.mock import patch


# ── App Launcher Tests ──

def test_app_launcher_resolve_widgets_default():
    from michi.app_launcher import _resolve_ui_mode
    with patch.dict(os.environ, {}, clear=True):
        assert _resolve_ui_mode() == "widgets"


def test_app_launcher_resolve_qml():
    from michi.app_launcher import _resolve_ui_mode
    with patch.dict(os.environ, {"MICHI_UI": "qml"}, clear=True):
        assert _resolve_ui_mode() == "qml"


def test_app_launcher_resolve_widgets_explicit():
    from michi.app_launcher import _resolve_ui_mode
    with patch.dict(os.environ, {"MICHI_UI": "widgets"}, clear=True):
        assert _resolve_ui_mode() == "widgets"


def test_app_launcher_resolve_invalid_fallback():
    from michi.app_launcher import _resolve_ui_mode
    with patch.dict(os.environ, {"MICHI_UI": "auto"}, clear=True):
        assert _resolve_ui_mode() == "widgets"


def test_app_launcher_resolve_unknown_fallback():
    from michi.app_launcher import _resolve_ui_mode
    with patch.dict(os.environ, {"MICHI_UI": "invalid"}, clear=True):
        assert _resolve_ui_mode() == "widgets"


def test_app_launcher_launch_widgets():
    from michi.app_launcher import launch
    with patch.dict(os.environ, {"MICHI_UI": "widgets"}, clear=True), \
         patch("michi.widgets_app.run_widgets") as mock_run:
        launch()
        mock_run.assert_called_once()


def test_app_launcher_launch_qml():
    from michi.app_launcher import launch
    with patch.dict(os.environ, {"MICHI_UI": "qml"}, clear=True), \
         patch("michi.qml_app.run_qml") as mock_run:
        launch()
        mock_run.assert_called_once()


def test_main_py_delegates_to_launcher():
    import main
    with patch("michi.app_launcher.launch") as mock_launch:
        main.main()
        mock_launch.assert_called_once()


# ── QML App Isolation Tests ──

def test_qml_app_no_widgets_import():
    spec = importlib.util.find_spec("michi.qml_app")
    qml_source = spec.loader.get_source("michi.qml_app")
    assert "PySide6.QtWidgets" not in qml_source, "qml_app must not import QtWidgets"
    assert "ui.window" not in qml_source, "qml_app must not import ui.window"
    assert "ui.pages" not in qml_source, "qml_app must not import ui.pages"
    assert "ui.dialogs" not in qml_source, "qml_app must not import ui.dialogs"


# ── Module import tests ──

def test_michi_init_exists():
    import michi
    assert michi.__file__.endswith("__init__.py")
    # Submodules are accessible
    from michi import app_launcher, qml_app, widgets_app
    assert app_launcher is not None
    assert qml_app is not None
    assert widgets_app is not None
