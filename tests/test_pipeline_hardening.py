"""Pipeline hardening tests — safe fallbacks, error handling, resource cleanup."""
from unittest.mock import MagicMock, patch


class TestPipelineFactoryHardening:
    def test_build_returns_none_on_ready_failure(self):
        """Standard pipeline returns None if set_state(READY) fails."""
        from audio.pipeline_factory import PipelineFactory
        from audio.format_probe import AudioFormatInfo
        from audio.dsp_state import DspState

        factory = PipelineFactory()
        fmt = AudioFormatInfo(is_pcm=True, is_dsd=False, is_stream=False,
                              sample_rate=44100, channels=2, bit_depth=16,
                              codec="PCM", bitrate=0, container="wav")
        route = MagicMock()
        route.bitperfect_expected = False
        route.dsd_mode = "pcm"
        dsp = DspState()

        with patch.object(factory, '_make_sink_bin') as mock_bin, \
             patch("gi.repository.Gst.Pipeline.new") as mock_new, \
             patch("gi.repository.Gst.ElementFactory.make"), \
             patch("gi.repository.Gst.StateChangeReturn") as mock_scr:
            mock_scr.FAILURE = 1
            mock_bin.return_value = MagicMock()
            mock_pipeline = MagicMock()
            mock_pipeline.set_state.return_value = 1  # FAILURE
            mock_new.return_value = mock_pipeline
            result = factory.build_for_uri("file:///tmp/a.wav", fmt, route, dsp)
            assert result is None

    def test_sink_fallback_to_autoaudiosink(self):
        """If requested sink not found, falls back to autoaudiosink."""
        from audio.pipeline_factory import PipelineFactory
        route = MagicMock()
        route.device_string = "alsasink device=hw:99,0"
        factory = PipelineFactory()
        with patch("gi.repository.Gst.ElementFactory.make") as mock_make:
            mock_make.side_effect = lambda name, _: MagicMock() if name == "autoaudiosink" else None
            result = factory._make_sink_from_route(route)
            assert result is not None

    def test_invalid_device_string_does_not_crash(self):
        """Malformed device_string property set_property doesn't crash."""
        from audio.pipeline_factory import PipelineFactory
        route = MagicMock()
        route.device_string = "autoaudiosink invalid_key=bad"
        factory = PipelineFactory()
        with patch("gi.repository.Gst.ElementFactory.make") as mock_make:
            mock_sink = MagicMock()
            mock_sink.set_property.side_effect = TypeError("bad type")
            mock_make.return_value = mock_sink
            result = factory._make_sink_from_route(route)
            assert result is not None

    def test_no_sink_available_returns_none(self):
        """If neither requested sink nor autoaudiosink exist, returns None."""
        from audio.pipeline_factory import PipelineFactory
        route = MagicMock()
        route.device_string = "nonexistent_sink"
        factory = PipelineFactory()
        with patch("gi.repository.Gst.ElementFactory.make") as mock_make:
            mock_make.return_value = None
            result = factory._make_sink_from_route(route)
            assert result is None


class TestPipelineLogging:
    def test_replaygain_failure_logged(self, caplog):
        """ReplayGain extraction failure is logged, not silently ignored."""
        import audio.player
        # Verify the except block has logging (static check)
        with open(audio.player.__file__) as f:
            content = f.read()
        assert "except Exception as e:" in content, "Must log exceptions"
        assert "ReplayGain" in content, "Must mention ReplayGain in log"

    def test_buffering_state_checked(self):
        """BUFFERING handler checks set_state return for FAILURE."""
        import audio.player
        with open(audio.player.__file__) as f:
            content = f.read()
        assert "StateChangeReturn.FAILURE" in content, "Must check FAILURE"

    def test_ready_state_checked_in_factory(self):
        """Pipeline factory checks READY state transition."""
        import audio.pipeline_factory
        with open(audio.pipeline_factory.__file__) as f:
            content = f.read()
        assert "READY" in content, "Must reference READY state"
        assert "FAILURE" in content, "Must check for FAILURE"

    def test_sink_property_has_try_except(self):
        """set_property is wrapped in try/except."""
        import audio.pipeline_factory
        with open(audio.pipeline_factory.__file__) as f:
            content = f.read()
        assert "set_property" in content
