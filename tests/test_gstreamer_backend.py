"""Tests for GStreamerBackend adapter — uses mocked engine."""

import pytest
from unittest.mock import MagicMock


class _FakePlaybackState:
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class TestGStreamerBackend:
    @pytest.fixture
    def engine(self):
        eng = MagicMock()
        eng.state = _FakePlaybackState.STOPPED
        eng.current = None
        eng._volume = 0.70
        return eng

    @pytest.fixture
    def backend(self, engine):
        from audio.backends.gstreamer_backend import GStreamerBackend
        return GStreamerBackend(engine)

    def test_backend_id(self, backend):
        assert backend.backend_id == "gstreamer"

    def test_capabilities(self, backend):
        caps = backend.capabilities
        assert caps.supports_eq is True
        assert caps.supports_radio is True
        assert caps.supports_bitperfect is False
        assert caps.supports_dsd is False

    def test_play_delegates(self, backend, engine):
        backend.play("/tmp/test.flac")
        engine.play.assert_called_once_with("/tmp/test.flac")

    def test_pause_delegates(self, backend, engine):
        backend.pause()
        engine.pause.assert_called_once()

    def test_resume_delegates(self, backend, engine):
        backend.resume()
        engine.resume.assert_called_once()

    def test_toggle_delegates(self, backend, engine):
        backend.toggle()
        engine.toggle.assert_called_once()

    def test_stop_delegates(self, backend, engine):
        backend.stop()
        engine.stop.assert_called_once()

    def test_seek_delegates(self, backend, engine):
        backend.seek(42.0)
        engine.seek.assert_called_once_with(42.0)

    def test_set_volume_delegates(self, backend, engine):
        backend.set_volume(75)
        engine.set_volume.assert_called_once_with(75)

    def test_set_queue_delegates(self, backend, engine):
        backend.set_queue(["a.flac", "b.flac"], start_index=1)
        engine.set_queue.assert_called_once_with(["a.flac", "b.flac"], 1)

    def test_enqueue_delegates(self, backend, engine):
        backend.enqueue(["a.flac"], play_now=False)
        engine.enqueue.assert_called_once_with(["a.flac"], False)

    def test_enqueue_next_delegates(self, backend, engine):
        backend.enqueue_next(["a.flac"])
        engine.enqueue_next.assert_called_once_with(["a.flac"])

    def test_clear_queue_delegates(self, backend, engine):
        backend.clear_queue()
        engine.clear_queue.assert_called_once()

    def test_play_next_delegates(self, backend, engine):
        backend.play_next()
        engine.play_next.assert_called_once()

    def test_play_prev_delegates(self, backend, engine):
        backend.play_prev()
        engine.play_prev.assert_called_once()

    def test_get_queue_delegates(self, backend, engine):
        engine.get_queue.return_value = [{"filepath": "a.flac"}]
        q = backend.get_queue()
        assert q == [{"filepath": "a.flac"}]

    def test_get_queue_index_delegates(self, backend, engine):
        engine.get_queue_index.return_value = 2
        assert backend.get_queue_index() == 2

    def test_get_snapshot_stopped(self, backend, engine):
        engine.state = _FakePlaybackState.STOPPED
        snap = backend.get_snapshot()
        assert snap.state == "stopped"
        assert snap.backend_id == "gstreamer"

    def test_get_snapshot_playing(self, backend, engine):
        from audio.player import PlaybackState
        engine.state = PlaybackState.PLAYING
        engine.current = "/tmp/song.flac"
        engine.get_queue_index.return_value = 0
        engine.get_queue.return_value = [{"filepath": "song.flac"}]
        snap = backend.get_snapshot()
        assert snap.state == "playing"
        assert snap.current_path == "/tmp/song.flac"

    def test_get_diagnostics(self, backend, engine):
        from audio.audio_diagnostics import AudioRouteDiagnostics
        engine.get_audio_diagnostics.return_value = AudioRouteDiagnostics(
            profile="standard", device_name="default",
            bitperfect_status="no", eq_active=True)
        diag = backend.get_diagnostics()
        assert diag.profile == "standard"
        assert diag.bitperfect_status == "no"
        assert diag.eq_active is True

    def test_shutdown_stops_engine(self, backend, engine):
        backend.shutdown()
        engine.stop.assert_called_once()

    def test_engine_property(self, backend, engine):
        assert backend.engine is engine
