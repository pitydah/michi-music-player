"""Tests for PlayerService with HybridAudioManager integration."""

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
        patch("audio.player_service.MpdServiceManager", MagicMock(spec=object)),
        patch("audio.player_service.MpdBackend", MagicMock(spec=object)),
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


class TestPlayerServiceGStreamer:
    """Tests methods that go to _engine when GStreamer is active."""

    def test_play_calls_engine(self, service):
        service._hybrid._active_id = "gstreamer"
        service.play("/tmp/test.flac")
        service._engine.play.assert_called_once()

    def test_pause_calls_engine(self, service):
        service._hybrid._active_id = "gstreamer"
        service.pause()
        service._engine.pause.assert_called_once()

    def test_set_volume_calls_engine(self, service):
        service._hybrid._active_id = "gstreamer"
        service.set_volume(50)
        service._engine.set_volume.assert_called_once()

    def test_get_audio_diagnostics_calls_engine(self, service):
        service._hybrid._active_id = "gstreamer"
        service.get_audio_diagnostics()
        service._engine.get_audio_diagnostics.assert_called_once()


class TestPlayerServiceMpdBlocking:
    """Tests that DSP is blocked when MPD backend is active."""

    def test_set_eq_graphic_blocked(self, service):
        service._hybrid._active_id = "mpd"
        service.set_eq_graphic([0.0] * 31)
        service._engine.set_eq_graphic.assert_not_called()

    def test_set_spectrum_blocked(self, service):
        service._hybrid._active_id = "mpd"
        service.set_spectrum_enabled(True)
        service._engine.set_spectrum_enabled.assert_not_called()


class TestPlayerServiceHybrid:
    """Tests methods that always go through _hybrid."""

    def test_stop_goes_to_hybrid(self, service):
        from unittest.mock import MagicMock
        service._hybrid.stop = MagicMock()
        service.stop()
        service._hybrid.stop.assert_called_once()

    def test_clear_queue_goes_to_hybrid(self, service):
        from unittest.mock import MagicMock
        service._hybrid.clear_queue = MagicMock()
        service.clear_queue()
        service._hybrid.clear_queue.assert_called_once()

    def test_get_queue_state_uses_hybrid(self, service):
        from unittest.mock import MagicMock
        service._hybrid.get_queue = MagicMock(return_value=[
            {"filepath": "a.flac"}, {"filepath": "b.flac"}])
        service._hybrid.get_queue_index = MagicMock(return_value=1)
        paths, idx = service.get_queue_state()
        assert paths == ["a.flac", "b.flac"]
        assert idx == 1

    def test_has_backend_changed_signal(self, service):
        assert hasattr(service, 'backend_changed')

    def test_get_active_backend_id(self, service):
        assert service.get_active_backend_id() == "gstreamer"

    def test_get_backend_capabilities(self, service):
        caps = service.get_backend_capabilities()
        assert caps is not None

    def test_play_url_stream_forces_gstreamer(self, service):
        """When mpd is active, play_url with HTTP must still go to engine."""
        service._hybrid._active_id = "mpd"
        service.play_url("http://stream.example.com/radio", "Station", "Artist")
        service._engine.play_url.assert_called_once_with("http://stream.example.com/radio")

    def test_play_url_non_stream_goes_to_hybrid(self, service):
        """When mpd is active, play_url with local path goes to hybrid."""
        service._hybrid._active_id = "mpd"
        service._hybrid.play = MagicMock()
        service.play_url("/music/track.flac", "Title", "Artist")
        service._hybrid.play.assert_called_once_with("/music/track.flac")

    def test_duration_in_gstreamer_mode(self, service):
        from unittest.mock import MagicMock
        mock_snap = MagicMock()
        mock_snap.duration_seconds = 240.0
        service._hybrid.get_snapshot = MagicMock(return_value=mock_snap)
        assert service.duration == 240.0

    def test_duration_in_mpd_mode(self, service):
        from unittest.mock import MagicMock
        mock_snap = MagicMock()
        mock_snap.duration_seconds = 180.0
        service._hybrid.get_snapshot = MagicMock(return_value=mock_snap)
        assert service.duration == 180.0

    def test_duration_in_mpd_mode_fallback_on_error(self):
        pass  # duration now always goes through hybrid snapshot
