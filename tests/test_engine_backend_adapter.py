"""Tests for the GStreamer engine public adapter and private transport."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal

from audio.backends.engine_backend_adapter import EngineBackendAdapter
from audio.player import PlaybackState


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
        self._queue: list[str] = []
        self._queue_index = -1
        self.current = ""
        self._audio_profile = "standard"
        self._replaygain = False
        self._spectrum_enabled = False
        self._eq = None
        self.last_seek = None

    def get_position_ns(self):
        return 0

    def set_volume(self, volume):
        clamped = max(0, min(100, int(volume)))
        self._volume = clamped / 100.0

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
        self.last_seek = seconds

    def toggle(self):
        if self.state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.resume()

    def set_queue(self, paths, start_index=0):
        self._queue = list(paths)
        self._queue_index = start_index if self._queue else -1

    def enqueue(self, paths, play_now=True):
        first_new = len(self._queue)
        self._queue.extend(paths)
        if play_now and paths:
            self._queue_index = first_new
            self.play(paths[0])

    def enqueue_next(self, paths):
        insert_at = max(0, self._queue_index + 1)
        self._queue[insert_at:insert_at] = paths

    def clear_queue(self):
        self._queue.clear()
        self._queue_index = -1

    def play_next(self):
        return True

    def play_prev(self):
        return True

    def get_queue(self):
        return [{"filepath": path} for path in self._queue]

    def get_queue_index(self):
        return self._queue_index


class FakeProperty:
    pass


class FakeVolumeElement:
    def __init__(self):
        self.volume = None

    def find_property(self, name):
        return FakeProperty() if name == "volume" else None

    def set_property(self, name, value):
        assert name == "volume"
        self.volume = value


class FakePipeline:
    def __init__(self):
        self.states = []
        self.seek_args = None
        self.volume_element = FakeVolumeElement()

    def set_state(self, state):
        self.states.append(state)
        from gi.repository import Gst

        return Gst.StateChangeReturn.SUCCESS

    def seek_simple(self, format_, flags, target):
        self.seek_args = (format_, flags, target)
        return True

    def get_by_name(self, name):
        return self.volume_element if name == "software-volume" else None

    def find_property(self, name):
        return None


@pytest.fixture
def engine():
    return FakeEngine()


@pytest.fixture
def adapter(engine):
    return EngineBackendAdapter(engine, internal_transport=False)


class TestEngineBackendAdapter:
    def test_backend_id(self, adapter):
        assert adapter.backend_id == "gstreamer"

    def test_name(self, adapter):
        assert adapter.name == "GStreamer (Engine)"

    def test_public_adapter_is_not_transport(self, adapter):
        assert adapter.is_internal_transport is False
        assert adapter.get_pipeline() is None

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
        assert adapter.get_snapshot().state == "playing"

    def test_pause_changes_state(self, adapter):
        adapter.play("/test/file.flac")
        adapter.pause()
        assert adapter.get_snapshot().state == "paused"

    def test_resume_after_pause(self, adapter):
        adapter.play("/test/file.flac")
        adapter.pause()
        adapter.resume()
        assert adapter.get_snapshot().state == "playing"

    def test_stop_changes_state(self, adapter):
        adapter.play("/test/file.flac")
        adapter.stop()
        assert adapter.get_snapshot().state == "stopped"

    def test_toggle_from_playing(self, adapter):
        adapter.play("/test/file.flac")
        adapter.toggle()
        assert adapter.get_snapshot().state == "paused"

    def test_toggle_from_paused(self, adapter):
        adapter.play("/test/file.flac")
        adapter.toggle()
        adapter.toggle()
        assert adapter.get_snapshot().state == "playing"

    def test_set_volume_range(self, adapter):
        for volume in [0, 25, 50, 75, 100]:
            adapter.set_volume(volume)
            assert adapter.get_snapshot().volume == volume

    def test_set_volume_clamps(self, adapter):
        adapter.set_volume(-10)
        assert adapter.get_snapshot().volume == 0
        adapter.set_volume(150)
        assert adapter.get_snapshot().volume == 100

    def test_seek_delegates_without_scaling(self, adapter, engine):
        adapter.seek(12.5)
        assert engine.last_seek == 12.5

    def test_snapshot_contains_current_path(self, adapter):
        adapter.play("/test/song.flac")
        assert adapter.get_snapshot().current_path == "/test/song.flac"

    def test_get_diagnostics_returns_struct(self, adapter):
        assert adapter.get_diagnostics().backend_id == "gstreamer"

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
        adapter.enqueue(["/a.flac"], play_now=False)
        adapter.clear_queue()
        assert adapter._engine._queue == []

    def test_get_queue(self, adapter):
        adapter.set_queue(["/a.flac"], 0)
        assert adapter.get_queue() == [{"filepath": "/a.flac"}]

    def test_shutdown_calls_stop(self, adapter):
        adapter.play("/test.flac")
        adapter.shutdown()
        assert adapter.get_snapshot().state == "stopped"

    def test_set_callbacks_stores_callables(self, adapter):
        callback = lambda state: state
        adapter.set_callbacks(on_state_changed=callback, invalid=None)
        assert adapter._callbacks == {"on_state_changed": callback}


class TestInternalPipelineTransport:
    @pytest.fixture
    def transport(self, engine):
        adapter = EngineBackendAdapter(engine, internal_transport=True)
        pipeline = FakePipeline()
        adapter.adopt_pipeline(pipeline)
        return adapter, pipeline

    def test_internal_transport_owns_pipeline(self, transport):
        adapter, pipeline = transport
        assert adapter.is_internal_transport is True
        assert adapter.get_pipeline() is pipeline

    def test_pause_resume_stop_do_not_recurse_into_engine(self, transport, engine):
        adapter, pipeline = transport
        engine.state = PlaybackState.PLAYING
        adapter.pause()
        adapter.resume()
        adapter.stop()
        assert len(pipeline.states) == 3
        assert engine.state == PlaybackState.PLAYING

    def test_seek_targets_gstreamer_time(self, transport):
        adapter, pipeline = transport
        adapter.seek(2.5)
        assert pipeline.seek_args is not None
        assert pipeline.seek_args[2] > 0

    def test_volume_targets_pipeline_element(self, transport):
        adapter, pipeline = transport
        assert adapter.set_volume(35) is True
        assert pipeline.volume_element.volume == pytest.approx(0.35)

    def test_internal_queue_operations(self, transport, engine):
        adapter, _ = transport
        adapter.set_queue(["/a.flac", "/b.flac"], 0)
        adapter.enqueue_next(["/next.flac"])
        adapter.enqueue(["/tail.flac"], play_now=False)
        assert engine._queue == ["/a.flac", "/next.flac", "/b.flac", "/tail.flac"]
        assert adapter.get_queue_index() == 0
