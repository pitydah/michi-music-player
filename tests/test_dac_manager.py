"""Tests for DacManager module."""
class TestDacManager:
    def test_init(self):
        from audio.dac_manager import DacManager
        dm = DacManager(None)
        assert dm is not None

    def test_refresh_devices(self):
        from audio.dac_manager import DacManager
        dm = DacManager(None)
        dm.refresh_devices()
        assert hasattr(dm, '_devices')

    def test_select_output_route_standard(self):
        from audio.dac_manager import DacManager
        from audio.output_profiles import get_profile
        from audio.format_probe import AudioFormatInfo
        dm = DacManager(None)
        dm.refresh_devices()
        profile = get_profile("standard")
        fmt = AudioFormatInfo(
            is_dsd=False, is_pcm=True, is_stream=False,
            codec="flac", sample_rate=44100, channels=2,
            bit_depth=16, bitrate=800000)
        route = dm.select_output_route(fmt, profile, None)
        assert route is not None

    def test_select_output_route_bitperfect(self):
        from audio.dac_manager import DacManager
        from audio.output_profiles import get_profile
        from audio.format_probe import AudioFormatInfo
        dm = DacManager(None)
        dm.refresh_devices()
        profile = get_profile("bitperfect_pcm")
        fmt = AudioFormatInfo(
            is_dsd=False, is_pcm=True, is_stream=False,
            codec="flac", sample_rate=44100, channels=2,
            bit_depth=16, bitrate=800000)
        route = dm.select_output_route(fmt, profile, None)
        assert route is not None
        # Without a real ALSA hw device, bitperfect falls back to hifi_pcm
        assert route.profile == "bitperfect_pcm" or route.fallback_suggestion

    def test_check_plugins(self):
        from audio.dac_manager import DacManager
        dm = DacManager(None)
        plugins = dm.check_plugins()
        assert isinstance(plugins, dict)

    def test_missing_plugins(self):
        from audio.dac_manager import DacManager
        dm = DacManager(None)
        missing = dm.missing_plugins()
        assert isinstance(missing, list)
