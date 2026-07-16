"""Tests for HomeAudioController."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._ctx = MagicMock()
    w._ctx.playback = MagicMock()
    w._ctx.playback.current = "http://stream.url"
    w._ctx.ha_connected = True
    w._ctx.ha_client = MagicMock()
    w._ctx.home_audio_view = None
    w._ctx.toast = MagicMock()
    w._ctx.player_bar = MagicMock()
    w._ctx.local_media_ctrl = None
    w._ctx.local_ip = "192.168.1.100"
    return w


@pytest.fixture
def ctrl(win):
    from legacy_widgets.ui.controllers.legacy_controllers.home_audio_controller import HomeAudioController
    c = HomeAudioController.__new__(HomeAudioController)
    from PySide6.QtCore import QObject
    QObject.__init__(c)
    c._win = win
    c._ctx = win._ctx
    c._svc = None
    return c


class TestHomeAudioController:
    def test_init_sets_win_ctx(self, ctrl, win):
        assert ctrl._win is win
        assert ctrl._ctx is win._ctx

    def test_is_connected_from_ctx(self, ctrl):
        assert ctrl.is_connected is True

    def test_is_connected_from_svc(self, ctrl, win):
        svc = MagicMock()
        svc.ha_connected.return_value = False
        ctrl._svc = svc
        assert ctrl.is_connected is False

    def test_ha_client_from_ctx(self, ctrl, win):
        assert ctrl.ha_client is win._ctx.ha_client

    def test_ha_client_from_svc(self, ctrl):
        svc = MagicMock()
        svc.ha_client = "svc_client"
        ctrl._svc = svc
        assert ctrl.ha_client == "svc_client"

    def test_get_devices_returns_empty_when_not_connected(self, ctrl):
        ctrl._ctx.ha_connected = False
        assert ctrl.get_devices() == []

    def test_get_devices_returns_empty_without_view(self, ctrl):
        assert ctrl.get_devices() == []

    def test_get_devices_returns_available(self, ctrl):
        d1 = {"available": True}
        d2 = {"available": False}
        view = MagicMock()
        view._devices = [d1, d2]
        ctrl._ctx.home_audio_view = view
        result = ctrl.get_devices()
        assert result == [d1]

    def test_cast_current_not_connected(self, ctrl):
        ctrl._ctx.ha_connected = False
        results = []
        ctrl.error_occurred.connect(lambda m: results.append(m))
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        assert "no conectado" in results[0]

    def test_cast_current_no_playback(self, ctrl):
        del ctrl._ctx.playback
        results = []
        ctrl.error_occurred.connect(lambda m: results.append(m))
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        assert "Reproductor" in results[0]

    def test_cast_current_no_current(self, ctrl):
        ctrl._ctx.playback.current = None
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        ctrl._ctx.toast.show.assert_called()

    def test_cast_current_stream_url(self, ctrl):
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        ctrl._ctx.ha_client.play_media.assert_called_with("e1", "http://stream.url", "music")

    def test_cast_current_local_file(self, ctrl):
        ctrl._ctx.playback.current = "/local/file.flac"
        lms = MagicMock()
        lms.register_file.return_value = "http://host/file.flac"
        ctrl._ctx.local_media_ctrl = lms
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        lms.register_file.assert_called_with("/local/file.flac", host="192.168.1.100")
        ctrl._ctx.ha_client.play_media.assert_called_with("e1", "http://host/file.flac", "music")

    def test_cast_current_local_file_no_lms(self, ctrl):
        ctrl._ctx.playback.current = "/local/file.flac"
        results = []
        ctrl.error_occurred.connect(lambda m: results.append(m))
        ctrl.cast_current({"entity_id": "e1", "name": "D1"})
        assert "Servidor local" in results[0]

    def test_on_cast_success_emits(self, ctrl):
        results = []
        ctrl.cast_started.connect(lambda e, n: results.append((e, n)))
        ctrl._on_cast_success("e1", "D1")
        ctrl._ctx.player_bar.set_transmit_active.assert_called_with(True, "D1")
        ctrl._ctx.toast.show.assert_called()
        assert results[0] == ("e1", "D1")

    def test_bind_view_does_nothing(self, ctrl):
        ctrl.bind_view(MagicMock())
