"""Tests for HybridAudioManager — backend switching and delegation."""

import pytest
from unittest.mock import MagicMock


def _make_fake_backend(backend_id: str):
    from audio.backends.types import BackendCapabilities
    b = MagicMock()
    b.backend_id = backend_id
    b.capabilities = BackendCapabilities(backend_id=backend_id, display_name=backend_id)
    b.get_queue.return_value = []
    b.get_queue_index.return_value = -1
    return b


class TestHybridAudioManager:
    @pytest.fixture
    def gst_backend(self):
        return _make_fake_backend("gstreamer")

    @pytest.fixture
    def mpd_backend(self):
        return _make_fake_backend("mpd")

    @pytest.fixture
    def manager(self, gst_backend):
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        m = HybridAudioManager(default_backend=gst_backend)
        return m

    def test_init_with_default(self, manager):
        assert manager.active_id == "gstreamer"
        assert manager.active is not None
        assert manager.is_fallback is False

    def test_init_no_default(self):
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        m = HybridAudioManager()
        assert m.active is None
        assert m.active_id == "gstreamer"

    def test_register_backend(self, manager, mpd_backend):
        manager.register(mpd_backend)
        assert manager.active_id == "gstreamer"

    def test_unregister_backend(self, manager, mpd_backend):
        manager.register(mpd_backend)
        manager.unregister("mpd")
        assert "mpd" not in manager._backends

    def test_switch_to_known_backend(self, manager, mpd_backend):
        manager.register(mpd_backend)
        result = manager.switch_to("mpd")
        assert result is True
        assert manager.active_id == "mpd"

    def test_switch_to_unknown_backend(self, manager):
        result = manager.switch_to("nonexistent")
        assert result is False
        assert manager.active_id == "gstreamer"

    def test_switch_same_backend(self, manager):
        result = manager.switch_to("gstreamer")
        assert result is True
        assert manager.active_id == "gstreamer"

    def test_choose_backend_standard_profile(self, manager):
        assert manager.choose_backend_for_profile("standard") == "gstreamer"

    def test_choose_backend_hifi_profile_no_mpd(self, manager):
        assert manager.choose_backend_for_profile("michi_hifi_mpd") == "gstreamer"

    def test_choose_backend_hifi_profile_with_mpd(self, manager, mpd_backend):
        manager.register(mpd_backend)
        assert manager.choose_backend_for_profile("michi_hifi_mpd") == "mpd"

    def test_choose_backend_bitperfect_profile(self, manager, mpd_backend):
        manager.register(mpd_backend)
        assert manager.choose_backend_for_profile("michi_bitperfect_mpd") == "mpd"

    def test_choose_backend_dsd_profile(self, manager, mpd_backend):
        manager.register(mpd_backend)
        assert manager.choose_backend_for_profile("michi_dsd_mpd") == "mpd"

    def test_choose_backend_server_profile(self, manager, mpd_backend):
        manager.register(mpd_backend)
        assert manager.choose_backend_for_profile("michi_server_renderer_mpd") == "mpd"

    def test_switch_for_profile_standard(self, manager):
        manager.switch_for_profile("standard")
        assert manager.active_id == "gstreamer"

    def test_switch_for_profile_mpd(self, manager, mpd_backend):
        manager.register(mpd_backend)
        manager.switch_for_profile("michi_hifi_mpd")
        assert manager.active_id == "mpd"

    def test_switch_for_profile_mpd_not_registered(self, manager):
        manager.switch_for_profile("michi_hifi_mpd")
        assert manager.active_id == "gstreamer"
        assert manager.is_fallback is True

    def test_switch_preserves_queue(self, manager, mpd_backend, gst_backend):
        gst_backend.get_queue.return_value = [
            {"filepath": "a.flac"}, {"filepath": "b.flac"}]
        gst_backend.get_queue_index.return_value = 1
        manager.register(mpd_backend)
        manager.switch_to("mpd")
        mpd_backend.set_queue.assert_called_once_with(["a.flac", "b.flac"], 1)

    def test_play_delegates(self, manager):
        manager.play("/tmp/test.flac")
        manager.active.play.assert_called_once_with("/tmp/test.flac")

    def test_pause_delegates(self, manager):
        manager.pause()
        manager.active.pause.assert_called_once()

    def test_resume_delegates(self, manager):
        manager.resume()
        manager.active.resume.assert_called_once()

    def test_toggle_delegates(self, manager):
        manager.toggle()
        manager.active.toggle.assert_called_once()

    def test_stop_delegates(self, manager):
        manager.stop()
        manager.active.stop.assert_called_once()

    def test_seek_delegates(self, manager):
        manager.seek(30.0)
        manager.active.seek.assert_called_once_with(30.0)

    def test_set_volume_delegates(self, manager):
        manager.set_volume(50)
        manager.active.set_volume.assert_called_once_with(50)

    def test_set_queue_delegates(self, manager):
        manager.set_queue(["a.flac"], start_index=0)
        manager.active.set_queue.assert_called_once_with(["a.flac"], 0)

    def test_enqueue_delegates(self, manager):
        manager.enqueue(["a.flac"], play_now=False)
        manager.active.enqueue.assert_called_once()

    def test_enqueue_next_delegates(self, manager):
        manager.enqueue_next(["a.flac"])
        manager.active.enqueue_next.assert_called_once()

    def test_clear_queue_delegates(self, manager):
        manager.clear_queue()
        manager.active.clear_queue.assert_called_once()

    def test_get_snapshot_delegates(self, manager):
        manager.get_snapshot()
        manager.active.get_snapshot.assert_called_once()

    def test_get_diagnostics_delegates(self, manager):
        manager.get_diagnostics()
        manager.active.get_diagnostics.assert_called_once()

    def test_get_capabilities_delegates(self, manager):
        manager.get_capabilities()
        assert manager.active.capabilities is not None

    def test_shutdown_all_backends(self, manager, mpd_backend):
        manager.register(mpd_backend)
        manager.shutdown()
        mpd_backend.shutdown.assert_called_once()

    def test_get_snapshot_no_active(self):
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        m = HybridAudioManager()
        snap = m.get_snapshot()
        assert snap.backend_id == "none"
        assert snap.state == "stopped"
        assert "No active" in snap.error

    def test_get_diagnostics_no_active(self):
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        m = HybridAudioManager()
        diag = m.get_diagnostics()
        assert diag.backend_id == "none"

    def test_get_capabilities_no_active(self):
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        m = HybridAudioManager()
        caps = m.get_capabilities()
        assert caps.backend_id == "none"
