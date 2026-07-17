"""Tests for EngineBackendAdapter — wraps GStreamerEngine as AudioBackend."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal

from audio.player import PlaybackState
from audio.backends.engine_backend_adapter import EngineBackendAdapter


class FakeEngine(QObject):
    position_changed = Signal(float)
    duration_changed = Signal(float)
    state_changed = Signal(object)
    queue_changed = Signal(list)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.state = PlaybackState.STOPPED
        self._volume = 0.7
        self._queue = []
        self._queue_index = -1
        self.current = ""
        self._audio_profile = "standard"
        self._replaygain = False
        self._spectrum_enabled = False
        self._eq = None

    def get_position_ns(self):
        return 0

    def set_volume(self, vol):
        self._volume = vol

    def stop(self):
        self.state = PlaybackState.STOPPED

    def play(self, path):
        self.current = path
        self.state = PlaybackState.PLAYING

    def pause(self):
        self.state = PlaybackState.PAUSED

    def resume(self):
        self.state = PlaybackState.PLAYING

    def seek(self, seconds):
        pass

    def toggle(self):
        if self.state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.resume()

    def play_next(self):
        return True

    def play_prev(self):
        return True


@pytest.fixture
def adapter():
    return EngineBackendAdapter(FakeEngine())


class TestEngineBackendAdapter:
    def test_backend_id(self, adapter):
        assert adapter.backend_id == "gstreamer"

    def test_name(self, adapter):
        assert adapter.name == "GStreamer (Engine)"

    def test_capabilities_are_dataclass(self, adapter):
        caps = adapter.capabilities
        assert caps.backend_id == "gstreamer"
        assert caps.supports_eq is True
        assert caps.supports_dsd is True

    def test_play_sets_current_path(self, adapter):
        adapter.play("/test/file.flac")
        assert adapter._engine.current == "/test/file.flac"

    def test_play_changes_state(self, adapter):
        adapter.play("/test/file.flac")
        snap = adapter.get_snapshot()
        assert snap.state == "playing"

    def test_pause_changes_state(self, adapter):
        adapter.play("/test/file.flac")
        adapter.pause()
        snap = adapter.get_snapshot()
        assert snap.state == "paused"

    def test_resume_after_pause(self, adapter):
        adapter.play("/test/file.flac")
        adapter.pause()
        adapter.resume()
        snap = adapter.get_snapshot()
        assert snap.state == "playing"

    def test_stop_changes_state(self, adapter):
        adapter.play("/test/file.flac")
        adapter.stop()
        snap = adapter.get_snapshot()
        assert snap.state == "stopped"

    def test_toggle_from_playing(self, adapter):
        adapter.play("/test/file.flac")
        adapter.toggle()
        snap = adapter.get_snapshot()
        assert snap.state == "paused"

    def test_toggle_from_paused(self, adapter):
        adapter.play("/test/file.flac")
        adapter.toggle()
        adapter.toggle()
        snap = adapter.get_snapshot()
        assert snap.state == "playing"

    def test_set_volume_range(self, adapter):
        for vol in [0, 25, 50, 75, 100]:
            adapter.set_volume(vol)
            snap = adapter.get_snapshot()
            assert snap.volume == vol

    def test_set_volume_clamps(self, adapter):
        adapter.set_volume(-10)
        snap = adapter.get_snapshot()
        assert snap.volume == 0

        adapter.set_volume(150)
        snap = adapter.get_snapshot()
        assert snap.volume == 100

    def test_snapshot_contains_current_path(self, adapter):
        adapter.play("/test/song.flac")
        snap = adapter.get_snapshot()
        assert snap.current_path == "/test/song.flac"

    def test_get_diagnostics_returns_struct(self, adapter):
        diag = adapter.get_diagnostics()
        assert diag.backend_id == "gstreamer"

    def test_play_next_returns_bool(self, adapter):
        assert adapter.play_next() is True

    def test_play_prev_returns_bool(self, adapter):
        assert adapter.play_prev() is True

    def test_set_queue(self, adapter):
        adapter.set_queue(["/a.flac", "/b.flac"], 0)
        assert adapter._engine._queue == ["/a.flac", "/b.flac"]

    def test_enqueue_appends(self, adapter):
        adapter.enqueue(["/c.flac"], play_now=False)
        assert "/c.flac" in adapter._engine._queue

    def test_clear_queue(self, adapter):
        adapter.enqueue(["/a.flac"])
        adapter.clear_queue()
        assert len(adapter._engine._queue) == 0

    def test_get_queue(self, adapter):
        adapter.set_queue(["/a.flac"], 0)
        q = adapter.get_queue()
        assert q == [{"filepath": "/a.flac"}]

    def test_shutdown_calls_stop(self, adapter):
        adapter.play("/test.flac")
        adapter.shutdown()
        snap = adapter.get_snapshot()
        assert snap.state == "stopped"

    def test_set_callbacks_noop(self, adapter):
        adapter.set_callbacks(on_state_changed=lambda s: None)
