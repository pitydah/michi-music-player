"""Verify all backends fulfill the AudioBackend contract."""
import pytest


def test_gstreamer_backend_has_all_methods():
    from audio.backends.gstreamer_backend import GStreamerAudioBackend
    backend = GStreamerAudioBackend()
    required = ['play', 'pause', 'resume', 'toggle', 'stop', 'seek',
                'set_volume', 'set_queue', 'enqueue', 'enqueue_next',
                'clear_queue', 'play_next', 'play_prev', 'get_queue',
                'get_queue_index', 'get_snapshot', 'get_diagnostics',
                'shutdown']
    for method in required:
        assert hasattr(backend, method), f"Missing: {method}"
    assert hasattr(type(backend), 'capabilities'), "Missing capabilities property"
    assert hasattr(type(backend), 'backend_id'), "Missing backend_id"


def test_mpd_backend_has_all_methods():
    try:
        from audio.backends.mpd_backend import MpdBackend
        backend = MpdBackend()
        required = ['play', 'pause', 'resume', 'stop', 'seek',
                    'set_volume', 'set_queue', 'enqueue', 'clear_queue',
                    'get_snapshot', 'shutdown']
        for method in required:
            assert hasattr(backend, method), f"MpdBackend missing: {method}"
    except ImportError:
        pytest.skip("MPD backend dependencies not available")


def test_volume_contract():
    from audio.backends.gstreamer_backend import GStreamerAudioBackend
    backend = GStreamerAudioBackend()
    for vol in [0, 1, 50, 99, 100]:
        backend.set_volume(vol)
        snap = backend.get_snapshot()
        assert snap.volume == vol, f"Volume {vol} -> {snap.volume}"
