"""Tests for PipelineFactory module."""


class TestPipelineFactory:
    def test_init(self):
        from audio.pipeline_factory import PipelineFactory
        factory = PipelineFactory()
        assert factory is not None

    def test_build_for_uri_standard(self):
        from audio.pipeline_factory import PipelineFactory
        from audio.audio_route_plan import AudioRoutePlan
        from audio.format_probe import AudioFormatInfo
        from audio.dsp_state import DspState

        factory = PipelineFactory()
        fmt = AudioFormatInfo(
            is_dsd=False, is_pcm=True, is_stream=False,
            codec="flac", sample_rate=44100, channels=2,
            bit_depth=16, bitrate=800000)
        route = AudioRoutePlan(
            device_string="autoaudiosink",
            use_audioconvert=True, use_audioresample=True,
            use_eq=True, use_replaygain=True,
            use_spectrum=True, use_transmit=False,
            bitperfect_expected=False, dsd_mode="")
        dsp = DspState()
        pipeline = factory.build_for_uri(
            "file:///tmp/test.flac", fmt, route, dsp, None)
        assert pipeline is not None

    def test_build_for_uri_bitperfect(self):
        from audio.pipeline_factory import PipelineFactory
        from audio.audio_route_plan import AudioRoutePlan
        from audio.format_probe import AudioFormatInfo

        factory = PipelineFactory()
        fmt = AudioFormatInfo(
            is_dsd=False, is_pcm=True, is_stream=False,
            codec="flac", sample_rate=44100, channels=2,
            bit_depth=16, bitrate=800000)
        route = AudioRoutePlan(
            device_string="alsasink",
            use_audioconvert=False, use_audioresample=False,
            use_eq=False, use_replaygain=False,
            use_spectrum=False, use_transmit=False,
            bitperfect_expected=True, dsd_mode="")
        pipeline = factory.build_for_uri(
            "file:///tmp/test.flac", fmt, route, None, None)
        assert pipeline is not None

    def test_build_playbin_audio_sink(self):
        from audio.pipeline_factory import PipelineFactory
        from audio.audio_route_plan import AudioRoutePlan
        from audio.dsp_state import DspState

        factory = PipelineFactory()
        route = AudioRoutePlan(
            device_string="autoaudiosink",
            use_audioconvert=True, use_audioresample=True,
            use_eq=True, use_replaygain=True,
            use_spectrum=True, use_transmit=False,
            bitperfect_expected=False, dsd_mode="")
        dsp = DspState()
        sink = factory.build_playbin_audio_sink(route, dsp)
        assert sink is not None

    def test_build_dff_pipeline(self):
        from audio.pipeline_factory import PipelineFactory
        from audio.audio_route_plan import AudioRoutePlan
        from audio.format_probe import AudioFormatInfo

        factory = PipelineFactory()
        fmt = AudioFormatInfo(
            is_dsd=True, is_pcm=False, is_stream=False,
            codec="dsd", sample_rate=2822400, channels=2,
            bit_depth=1, bitrate=0)
        route = AudioRoutePlan(
            device_string="autoaudiosink",
            use_audioconvert=True, use_audioresample=True,
            use_eq=False, use_replaygain=False,
            use_spectrum=False, use_transmit=False,
            bitperfect_expected=False, dsd_mode="pcm")
        pipeline = factory.build_dff_pipeline("/tmp/test.dff", fmt, route)
        assert pipeline is not None

    def test_dop_without_env(self):
        from audio.pipeline_factory import PipelineFactory
        from audio.audio_route_plan import AudioRoutePlan
        from audio.format_probe import AudioFormatInfo

        factory = PipelineFactory()
        fmt = AudioFormatInfo(
            is_dsd=True, is_pcm=False, is_stream=False,
            codec="dsd", sample_rate=2822400, channels=2,
            bit_depth=1, bitrate=0)
        route = AudioRoutePlan(
            device_string="alsasink",
            use_audioconvert=False, use_audioresample=False,
            use_eq=False, use_replaygain=False,
            use_spectrum=False, use_transmit=False,
            bitperfect_expected=False, dsd_mode="dop")
        pipeline = factory._build_dop("file:///tmp/test.dsf", fmt, route)
        # Returns None without env var
        assert pipeline is None
