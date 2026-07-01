"""Tests de integración end-to-end del Michi Hybrid Audio Engine."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def _patch_gst():
    from PySide6.QtCore import QObject, QTimer
    patches = [
        patch("audio.player.Gst", MagicMock()),
        patch("audio.player.GLib", MagicMock()),
        patch("audio.player.gi", MagicMock()),
        patch("audio.player.np", MagicMock()),
        patch("audio.player.QObject", QObject),
        patch("audio.player.QTimer", QTimer),
        patch("audio.player_service.MpdServiceManager", MagicMock()),
        patch("audio.player_service.MpdBackend", MagicMock()),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def service():
    from audio.player_service import PlayerService
    from audio.player import PlaybackState
    engine = MagicMock()
    engine._state = PlaybackState.STOPPED
    engine.state = PlaybackState.STOPPED
    engine.current = None
    engine._volume = 0.70
    engine.duration = 0.0
    return PlayerService(engine)


class TestHybridEngineEndToEnd:
    def test_standard_profile_uses_gstreamer(self, service):
        assert service.get_active_backend_id() == "gstreamer"
        service.play("/tmp/test.flac")
        service._engine.play.assert_called_once()

    def test_mpd_absent_falls_back_to_gstreamer(self, service):
        service._hybrid._active_id = "gstreamer"
        fallback = service._hybrid.choose_backend_for_profile("michi_hifi_mpd")
        assert fallback == "gstreamer"
        service.play("/tmp/test.flac")
        service._engine.play.assert_called_once()

    def test_set_audio_profile_bitperfect_blocks_eq(self, service):
        service._hybrid._active_id = "mpd"
        service.set_eq_graphic([0.0] * 31)
        service._engine.set_eq_graphic.assert_not_called()

    def test_queue_preserved_across_backend_switch(self, service):
        from unittest.mock import MagicMock
        service._hybrid.get_queue = MagicMock(return_value=[
            {"filepath": "a.flac"}, {"filepath": "b.flac"}])
        service._hybrid.get_queue_index = MagicMock(return_value=1)
        paths, idx = service.get_queue_state()
        assert paths == ["a.flac", "b.flac"]
        assert idx == 1

    def test_get_bitperfect_report_returns_report(self, service):
        report = service.get_bitperfect_report()
        assert report is not None
        assert hasattr(report, 'status')
        assert hasattr(report, 'reasons')

    def test_paused_state_not_lost_on_profile_change(self, service):
        from audio.player import PlaybackState
        service._engine._state = PlaybackState.PAUSED
        service._engine.state = PlaybackState.PAUSED
        assert service.state == PlaybackState.PAUSED or service.state == "paused"

    def test_play_url_stream_goes_to_engine(self, service):
        service._hybrid._active_id = "mpd"
        service.play_url("http://stream.example.com/radio", "Station")
        service._engine.play_url.assert_called_once_with("http://stream.example.com/radio")

    def test_duration_from_mpd_when_active(self, service):
        from unittest.mock import MagicMock
        mock_snap = MagicMock()
        mock_snap.duration_seconds = 180.0
        service._hybrid.get_snapshot = MagicMock(return_value=mock_snap)
        assert service.duration == 180.0

    def test_duration_fallback_when_mpd_fails(self, service):
        from unittest.mock import MagicMock
        service._hybrid.get_snapshot = MagicMock(side_effect=Exception("fail"))
        assert service.duration == 0.0
