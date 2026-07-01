"""Tests for audio profile → backend selection rules."""



def _make_profile(key: str, preferred_backend: str = "auto"):
    from audio.output_profiles import AudioOutputProfile
    return AudioOutputProfile(
        key=key,
        name=key,
        description=f"Test profile {key}",
        preferred_backend=preferred_backend,
    )


class TestProfileBackendSelection:
    def test_standard_profile_chooses_gstreamer(self):
        from audio.output_profiles import get_profile
        from audio.backends.hybrid_audio_manager import HybridAudioManager
        mgr = HybridAudioManager()
        result = mgr.choose_backend_for_profile(get_profile("standard").key)
        assert result == "gstreamer"

    def test_bitperfect_profile_requests_mpd(self):
        from audio.backends.hybrid_audio_manager import MPD_PROFILES
        assert "michi_bitperfect_mpd" in MPD_PROFILES

    def test_hifi_profile_requests_mpd(self):
        from audio.backends.hybrid_audio_manager import MPD_PROFILES
        assert "michi_hifi_mpd" in MPD_PROFILES

    def test_dsd_profile_requests_mpd(self):
        from audio.backends.hybrid_audio_manager import MPD_PROFILES
        assert "michi_dsd_mpd" in MPD_PROFILES

    def test_server_profile_requests_mpd(self):
        from audio.backends.hybrid_audio_manager import MPD_PROFILES
        assert "michi_server_renderer_mpd" in MPD_PROFILES

    def test_preferred_backend_field_exists(self):
        profile = _make_profile("test")
        assert profile.preferred_backend == "auto"

    def test_backend_can_be_set_on_profile(self):
        profile = _make_profile("mpd_test", preferred_backend="mpd")
        assert profile.preferred_backend == "mpd"
