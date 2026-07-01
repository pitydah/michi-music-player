"""Tests for HybridAudioManager — backend selection, switching, fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from audio.backends.hybrid_audio_manager import HybridAudioManager, MPD_PROFILES


def _mock_backend(backend_id: str):
    b = MagicMock()
    b.backend_id = backend_id
    return b


class TestChooseBackend:
    def test_gstreamer_profile_returns_gstreamer(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        assert mgr.choose_backend_for_profile("standard") == "gstreamer"

    def test_hifi_mpd_profile_without_mpd_falls_back(self):
        mgr = HybridAudioManager(default_backend=_mock_backend("gstreamer"))
        result = mgr.choose_backend_for_profile("michi_hifi_mpd")
        assert result == "gstreamer"
        assert mgr.is_fallback is True

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
