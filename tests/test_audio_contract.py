"""Verify all backends fulfill the AudioBackend contract."""
import pytest

from audio.player import PlaybackState


def _make_mock_engine():
    """Create a mock engine with enough structure for the adapter."""
    from PySide6.QtCore import QObject, Signal

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

        def set_volume(self, volume):
            clamped = max(0, min(100, int(volume)))
            self._volume = clamped / 100.0

        def stop(self):
            self.state = PlaybackState.STOPPED

    return FakeEngine()


def test_engine_backend_adapter_has_all_methods():
    from audio.backends.engine_backend_adapter import EngineBackendAdapter

    backend = EngineBackendAdapter(_make_mock_engine(), internal_transport=False)
    required = [
        "play", "pause", "resume", "toggle", "stop", "seek",
        "set_volume", "set_queue", "enqueue", "enqueue_next",
        "clear_queue", "play_next", "play_prev", "get_queue",
        "get_queue_index", "get_snapshot", "get_diagnostics",
        "shutdown",
    ]
    for method in required:
        assert hasattr(backend, method), f"Missing: {method}"
    assert hasattr(type(backend), "capabilities"), "Missing capabilities property"
    assert hasattr(type(backend), "backend_id"), "Missing backend_id"
    assert backend.backend_id == "gstreamer"


def test_mpd_backend_has_all_methods():
    try:
        from audio.backends.mpd_backend import MpdBackend

        backend = MpdBackend()
        required = [
            "play", "pause", "resume", "stop", "seek",
            "set_volume", "set_queue", "enqueue", "clear_queue",
            "get_snapshot", "shutdown",
        ]
        for method in required:
            assert hasattr(backend, method), f"MpdBackend missing: {method}"
    except ImportError:
        pytest.skip("MPD backend dependencies not available")


def test_volume_contract():
    from audio.backends.engine_backend_adapter import EngineBackendAdapter

    backend = EngineBackendAdapter(_make_mock_engine(), internal_transport=False)
    for volume in [0, 1, 50, 99, 100]:
        backend.set_volume(volume)
        snapshot = backend.get_snapshot()
        assert snapshot.volume == volume, f"Volume {volume} -> {snapshot.volume}"


def test_adapter_capabilities_include_eq():
    from audio.backends.engine_backend_adapter import EngineBackendAdapter

    backend = EngineBackendAdapter(_make_mock_engine(), internal_transport=False)
    capabilities = backend.capabilities
    assert capabilities.supports_eq is True
    assert capabilities.supports_replaygain is True
    assert capabilities.supports_spectrum is True
    assert capabilities.supports_dsd is True
    assert capabilities.supports_dop is True
