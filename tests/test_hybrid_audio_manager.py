"""Tests for HybridAudioManager — backend selection, switching, fallback."""

from __future__ import annotations

from unittest.mock import MagicMock


from audio.backends.hybrid_audio_manager import (
    HybridAudioManager,
    MPD_PROFILES,
    BACKEND_STATE_UNINITIALIZED,
    BACKEND_STATE_READY,
    BACKEND_STATE_DEGRADED,
    BACKEND_STATE_FAILED,
)


def _mock_backend(backend_id: str):
    b = MagicMock()
    b.backend_id = backend_id
    b.is_ready.return_value = True
    b.is_playing.return_value = False
    return b


class TestChooseBackend:
    def test_gstreamer_profile_returns_gstreamer(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.choose_backend_for_profile("standard") == "gstreamer"

    def test_hifi_mpd_profile_targets_mpd_without_preregistering(self):
        # choose_backend_for_profile no longer pre-falls-back; it returns the
        # desired backend and lets switch_for_profile ensure availability /
        # fall back via ensure_backend_available.
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        result = mgr.choose_backend_for_profile("michi_hifi_mpd")
        assert result == "mpd"
        assert mgr.is_fallback is False

    def test_hifi_mpd_profile_with_mpd_returns_mpd(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mgr.register(_mock_backend("mpd"))
        result = mgr.choose_backend_for_profile("michi_hifi_mpd")
        assert result == "mpd"
        assert mgr.is_fallback is False

    def test_all_mpd_profiles_recognized(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mgr.register(_mock_backend("mpd"))
        for profile in MPD_PROFILES:
            assert mgr.choose_backend_for_profile(profile) == "mpd"

    def test_unknown_profile_falls_to_gstreamer(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.choose_backend_for_profile("nonexistent_profile") == "gstreamer"


class TestSwitchTo:
    def test_switch_to_same_backend_returns_true(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.switch_to("gstreamer") is True

    def test_switch_to_unknown_returns_false(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.switch_to("unknown") is False

    def test_switch_to_registered_backend(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mpd = _mock_backend("mpd")
        mgr.register(mpd)
        assert mgr.switch_to("mpd") is True
        assert mgr.active_id == "mpd"


class TestSwitchForProfile:
    def test_gstreamer_to_mpd_via_profile(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mpd = _mock_backend("mpd")
        mgr.register(mpd)
        assert mgr.switch_for_profile("michi_hifi_mpd") is True
        assert mgr.active_id == "mpd"

    def test_profile_fallback_to_gstreamer(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.switch_for_profile("michi_hifi_mpd") is True
        assert mgr.active_id == "gstreamer"
        assert mgr.is_fallback is True

    def test_standard_profile_no_switch(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.switch_for_profile("standard") is True
        assert mgr.active_id == "gstreamer"
        assert mgr.is_fallback is False


class TestFallback:
    def test_fallback_to_default(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mpd = _mock_backend("mpd")
        mgr.register(mpd)
        mgr.mark_fallback(True)
        mgr.switch_to("mpd")
        assert mgr.active_id == "mpd"
        assert mgr.fallback_to_default("test") is True
        assert mgr.active_id == "gstreamer"


class TestProperties:
    def test_active_returns_backend(self):
        gst = _mock_backend("gstreamer")
        mgr = HybridAudioManager(default_backend=gst)
        assert mgr.active is gst

    def test_active_id_returns_string(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.active_id == "gstreamer"

    def test_active_returns_none_when_no_backend(self):
        mgr = HybridAudioManager()
        assert mgr.active is None


class TestBackendStateMachine:
    def test_no_default_backend_is_uninitialized(self):
        mgr = HybridAudioManager()
        assert mgr.backend_state == BACKEND_STATE_UNINITIALIZED

    def test_ready_default_backend_is_ready(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.backend_state == BACKEND_STATE_READY

    def test_register_flips_uninitialized_to_ready(self):
        mgr = HybridAudioManager()
        assert mgr.backend_state == BACKEND_STATE_UNINITIALIZED
        mgr.register(_mock_backend("gstreamer"))
        assert mgr.backend_state == BACKEND_STATE_READY

    def test_switch_for_profile_sets_ready_on_success(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mgr.register(_mock_backend("mpd"))
        assert mgr.switch_for_profile("michi_hifi_mpd") is True
        assert mgr.backend_state == BACKEND_STATE_READY

    def test_fallback_to_default_is_degraded(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mgr.register(_mock_backend("mpd"))
        mgr.switch_to("mpd")
        assert mgr.fallback_to_default("test") is True
        assert mgr.backend_state == BACKEND_STATE_DEGRADED


class TestTransactionalSwitch:
    def test_roll_back_when_target_not_ready(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        mpd = _mock_backend("mpd")
        mpd.is_ready.return_value = False
        mgr.register(mpd)

        result = mgr.switch_for_profile("michi_hifi_mpd")

        assert result is False
        # Active backend restored to the previous one.
        assert mgr.active_id == "gstreamer"

    def test_roll_back_preserves_state_on_failure(self):
        gst = _mock_backend("gstreamer")
        mgr = HybridAudioManager(default_backend=gst)
        mpd = _mock_backend("mpd")
        mpd.is_ready.return_value = False
        mgr.register(mpd)
        mgr.switch_for_profile("michi_hifi_mpd")  # fails + rolls back

        assert mgr.backend_state == BACKEND_STATE_READY
        assert mgr.active is gst

    def test_unregistered_target_marks_failed(self):
        # Default backend is mpd; a standard profile needs gstreamer, which is
        # not registered → switch_for_profile must fail and mark state FAILED.
        mgr = HybridAudioManager(default_backend=_mock_backend("mpd"))
        result = mgr.switch_for_profile("standard")
        assert result is False
        assert mgr.backend_state == BACKEND_STATE_FAILED
        assert mgr.active_id == "mpd"


class TestDualPlaybackGuard:
    def test_play_stops_active_when_playing(self):
        gst = _mock_backend("gstreamer")
        gst.is_playing.return_value = True
        mgr = HybridAudioManager(default_backend=gst)

        mgr.play("/track.flac")

        gst.stop.assert_called_once()
        gst.play.assert_called_once_with("/track.flac")

    def test_play_does_not_stop_when_not_playing(self):
        gst = _mock_backend("gstreamer")
        gst.is_playing.return_value = False
        mgr = HybridAudioManager(default_backend=gst)

        mgr.play("/track.flac")

        gst.stop.assert_not_called()
        gst.play.assert_called_once_with("/track.flac")

    def test_play_noop_without_active_backend(self):
        mgr = HybridAudioManager()
        # Should not raise when there is no active backend.
        mgr.play("/track.flac")
