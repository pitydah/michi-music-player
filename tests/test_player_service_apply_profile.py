"""Tests for transactional PlayerService.apply_profile (Patch 2).

Covers the prepare -> apply -> verify -> persist lifecycle, including the
explicit profile states and rollback on verification failure.
"""
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
    engine.state = PlaybackState.STOPPED
    engine._volume = 0.70
    engine.duration = 0.0
    return PlayerService(engine)


class TestApplyProfileTransactional:
    def test_unknown_profile_returns_unknown(self, service):
        from audio.output_profiles import PROFILE_FAILED
        result = service.apply_profile("does_not_exist")
        assert result["ok"] is False
        assert result["code"] == "UNKNOWN_PROFILE"
        assert result["state"] == PROFILE_FAILED

    def test_success_returns_verified_persisted(self, service):
        from audio.output_profiles import PROFILE_PERSISTED
        with patch.object(service, "switch_backend_for_profile", return_value=True) as sw:
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("standard")
        assert result["ok"] is True
        assert result["verified"] is True
        assert result["persisted"] is True
        assert result["state"] == PROFILE_PERSISTED
        assert result["active_profile"] == "standard"
        assert result["active_backend"] == "gstreamer"
        sw.assert_called_once_with("standard")

    def test_backend_failure_propagates_without_verify(self, service):
        from audio.output_profiles import PROFILE_FAILED
        # MPD profile whose backend switch fails -> fell back to gstreamer.
        with patch.object(service, "switch_backend_for_profile", return_value=False):
            service._hybrid._active_id = "gstreamer"
            result = service.apply_profile("michi_hifi_mpd")
        assert result["ok"] is False
        assert result["code"] == "BACKEND_FAILED"
        assert result["state"] == PROFILE_FAILED
        assert result["fallback"] is True

    def test_verify_failure_rolls_back_to_previous(self, service):
        from audio.player import PlaybackState
        from audio.output_profiles import PROFILE_FAILED
        # Active backend not ready -> verify fails and previous profile is restored.
        service._engine.state = PlaybackState.FAILED
        service._active_profile_id = "hifi_pcm"
        with patch.object(service, "switch_backend_for_profile", return_value=True) as sw:
            result = service.apply_profile("standard")
        assert result["ok"] is False
        assert result["code"] == "VERIFY_FAILED"
        assert result["rollback"] is True
        assert result["state"] == PROFILE_FAILED
        assert result["active_profile"] == "hifi_pcm"
        # apply + rollback => two switches, the second restores the previous profile
        assert sw.call_count == 2
        assert sw.call_args_list[1].args[0] == "hifi_pcm"

    def test_set_profile_delegates_and_returns_real_result(self, service):
        """set_profile must not fabricate ok=True when the switch failed."""
        with patch.object(service, "switch_backend_for_profile", return_value=False):
            service._hybrid._active_id = "gstreamer"
            result = service.set_profile("michi_hifi_mpd")
        assert result["ok"] is False
        assert result["fallback"] is True

    def test_success_persists_setting(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True):
            service._hybrid._active_id = "gstreamer"
            with patch("core.settings_manager.set_") as set_:
                result = service.apply_profile("hifi_pcm")
        assert result["ok"] is True
        set_.assert_called_with("audio/profile", "hifi_pcm")

    def test_set_audio_profile_delegates_to_apply(self, service):
        with patch.object(service, "switch_backend_for_profile", return_value=True):
            service._hybrid._active_id = "gstreamer"
            service.set_audio_profile("hifi_pcm")
        assert service.get_active_profile_id() == "hifi_pcm"
