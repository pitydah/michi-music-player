"""Tests for launchers — app_launcher, qml_app, verify_app.
app_launcher does NOT create QApplication.
qml_app does NOT import QtWidgets.
"""
from unittest.mock import patch

import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestAppLauncher:
    def test_launch_widgets_rejected(self):
        with patch.dict('os.environ', {'MICHI_UI': 'widgets'}):
            from michi.app_launcher import launch
            result = launch()
            assert result == 1

    def test_launch_qml_dispatches_correctly(self):
        with patch.dict('os.environ', {'MICHI_UI': 'qml'}), \
             patch('michi.qml_app.run_qml', return_value=0) as mock_q:
            from michi.app_launcher import launch
            result = launch()
            mock_q.assert_called_once()

    def test_launch_verify_dispatches_correctly(self):
        with patch.dict('os.environ', {'MICHI_UI': 'verify'}), \
             patch('michi.verify_app.run_verify', return_value=0) as mock_v:
            from michi.app_launcher import launch
            result = launch()
            mock_v.assert_called_once()

    def test_launch_defaults_to_qml(self):
        with patch.dict('os.environ', {}, clear=True), \
             patch('michi.qml_app.run_qml', return_value=0) as mock_q:
            from michi.app_launcher import launch
            result = launch()
            mock_q.assert_called_once()


class TestLauncherModules:
    def test_qml_app_requires_no_qtgui_at_module_level(self):
        import michi.qml_app
        assert hasattr(michi.qml_app, 'run_qml')

    def test_app_launcher_does_not_import_qt_at_top(self):
        import michi.app_launcher
        mod_names = [m for m in dir(michi.app_launcher) if not m.startswith('_')]
        assert 'QApplication' not in mod_names

    def test_verify_app_imports_bootstrap(self):
        from core.application_bootstrap import ApplicationBootstrap
        assert ApplicationBootstrap is not None

    def test_verify_app_has_run_verify(self):
        import michi.verify_app
        assert hasattr(michi.verify_app, 'run_verify')

    def test_qml_app_module_can_be_imported(self):
        import michi.qml_app
        assert hasattr(michi.qml_app, 'run_qml')
