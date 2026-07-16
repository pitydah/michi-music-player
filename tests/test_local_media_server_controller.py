"""Tests for LocalMediaServerController."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._ctx = MagicMock()
    w._ctx.local_media = None
    return w


@pytest.fixture
def ctrl(win):
    from legacy_widgets.ui.controllers.legacy_controllers.local_media_server_controller import (
        LocalMediaServerController,
    )
    c = LocalMediaServerController.__new__(LocalMediaServerController)
    from PySide6.QtCore import QObject
    QObject.__init__(c)
    c._win = win
    c._ctx = win._ctx
    c._port = 8125
    c._server = None
    return c


class TestLocalMediaServerController:
    def test_init_sets_win_ctx(self, ctrl, win):
        assert ctrl._win is win
        assert ctrl._ctx is win._ctx

    def test_is_running_returns_false_when_not_initialized(self, ctrl):
        assert ctrl.is_running is False

    def test_is_running_returns_true(self, ctrl):
        server = MagicMock()
        server.is_running = True
        ctrl._server = server
        assert ctrl.is_running is True

    def test_start_emits_error_when_no_server(self, ctrl):
        results = []
        ctrl.error_occurred.connect(lambda m: results.append(m))
        ctrl.start()
        assert results == ["LocalMediaServer not initialized"]

    def test_start_skips_if_already_running(self, ctrl):
        server = MagicMock()
        server.is_running = True
        ctrl._server = server
        results = []
        ctrl.server_started.connect(lambda p: results.append(p))
        ctrl.start()
        server.configure.assert_not_called()
        assert results == []

    def test_start_configures_and_starts(self, ctrl):
        server = MagicMock()
        server.is_running = False
        ctrl._server = server
        results = []
        ctrl.server_started.connect(lambda p: results.append(p))
        ctrl.start(8888)
        server.configure.assert_called_with(8888)
        server.start.assert_called_once()
        assert results == [8888]

    def test_stop_does_nothing_when_not_running(self, ctrl):
        ctrl.stop()

    def test_stop_stops_server(self, ctrl):
        server = MagicMock()
        server.is_running = True
        ctrl._server = server
        results = []
        ctrl.server_stopped.connect(lambda: results.append(True))
        ctrl.stop()
        server.stop.assert_called_once()
        assert results == [True]

    def test_register_file_raises_without_server(self, ctrl):
        with pytest.raises(ValueError, match="not initialized"):
            ctrl.register_file("/path/to/file.flac")

    def test_register_file_starts_if_not_running(self, ctrl):
        server = MagicMock()
        server.is_running = False
        server.register_file.return_value = "http://host/file.flac"
        ctrl._server = server
        url = ctrl.register_file("/path/to/file.flac", host="myhost")
        server.start.assert_called_once()
        server.register_file.assert_called_with("/path/to/file.flac", host="myhost")
        assert url == "http://host/file.flac"

    def test_register_file_returns_url(self, ctrl):
        server = MagicMock()
        server.is_running = True
        server.register_file.return_value = "http://host/file.flac"
        ctrl._server = server
        url = ctrl.register_file("/path/to/file.flac", host="myhost")
        server.register_file.assert_called_with("/path/to/file.flac", host="myhost")
        assert url == "http://host/file.flac"
