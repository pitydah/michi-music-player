"""Tests for DSD detection and DoP pipeline routing — fully mocked."""
import pytest
from unittest.mock import MagicMock, patch


def _dispatch_build_for_uri(factory, uri, fmt, route, dsp=None, transmit_device=None):
    """Mirrors PipelineFactory.build_for_uri dispatch logic for test isolation."""
    if route.bitperfect_expected and fmt.is_pcm and not fmt.is_dsd:
        return factory._build_bitperfect(uri, route)
    if fmt.is_dsd and route.dsd_mode == "pcm":
        return factory._build_dsd_to_pcm(uri, fmt, route)
    if fmt.is_dsd and route.dsd_mode == "dop":
        return factory._build_dop(uri, fmt, route)
    return factory._build_standard(uri, route, dsp, transmit_device)


class TestDopPipeline:
    """DoP (DSD over PCM) detection, pipeline config, and fallback."""

    @pytest.fixture
    def probe_dsd(self):
        from audio.format_probe import AudioFormatInfo
        return AudioFormatInfo(
            path_or_uri="/tmp/test.dsf", container="dsf", codec="DSD",
            is_dsd=True, is_dsf=True, sample_rate=2822400,
            dsd_rate=2822400, dsd_speed="DSD64", channels=2,
        )

    @pytest.fixture
    def probe_pcm(self):
        from audio.format_probe import AudioFormatInfo
        return AudioFormatInfo(
            path_or_uri="/tmp/test.flac", container="flac", codec="FLAC",
            is_dsd=False, is_pcm=True, sample_rate=44100, channels=2,
        )

    # ── 1. DSD detection ──

    def test_dop_detection(self):
        from audio.format_probe import probe_format
        info = probe_format("/music/test.dsf")
        assert info.is_dsd is True
        assert info.is_dsf is True
        assert info.codec == "DSD"
        assert info.dsd_rate > 0

    def test_dop_detection_dff(self):
        from audio.format_probe import probe_format
        info = probe_format("/music/test.dff")
        assert info.is_dsd is True
        assert info.is_dff is True
        assert info.codec == "DSD"

    def test_dop_detection_pcm_is_not_dsd(self):
        from audio.format_probe import probe_format
        info = probe_format("/music/test.flac")
        assert info.is_dsd is False
        assert info.is_pcm is True

    # ── 2. DoP pipeline config vs PCM ──

    def test_dop_pipeline_config_selects_build_dop(self, probe_dsd):
        from audio.audio_route_plan import AudioRoutePlan
        route = AudioRoutePlan(dsd_mode="dop")
        factory = MagicMock()
        factory._build_dop = MagicMock(return_value="dop-pipeline")
        factory._build_dsd_to_pcm = MagicMock(return_value="pcm-pipeline")
        factory._build_bitperfect = MagicMock(return_value="bp-pipeline")

        result = _dispatch_build_for_uri(factory, "file:///test.dsf", probe_dsd, route)

        factory._build_dop.assert_called_once()
        factory._build_dsd_to_pcm.assert_not_called()
        assert result == "dop-pipeline"

    def test_dop_pipeline_config_dsd_to_pcm(self, probe_dsd):
        from audio.audio_route_plan import AudioRoutePlan
        route = AudioRoutePlan(dsd_mode="pcm")
        factory = MagicMock()
        factory._build_dop = MagicMock(return_value="dop-pipeline")
        factory._build_dsd_to_pcm = MagicMock(return_value="pcm-pipeline")
        factory._build_bitperfect = MagicMock()

        result = _dispatch_build_for_uri(factory, "file:///test.dsf", probe_dsd, route)

        factory._build_dsd_to_pcm.assert_called_once()
        factory._build_dop.assert_not_called()
        assert result == "pcm-pipeline"

    def test_dop_pipeline_config_standard_for_pcm(self, probe_pcm):
        from audio.audio_route_plan import AudioRoutePlan
        route = AudioRoutePlan(dsd_mode="")
        factory = MagicMock()
        factory._build_standard = MagicMock(return_value="std-pipeline")

        result = _dispatch_build_for_uri(
            factory, "file:///test.flac", probe_pcm, route,
            dsp=MagicMock(), transmit_device=None)

        factory._build_standard.assert_called_once()
        assert result == "std-pipeline"

    def test_dop_pipeline_config_bitperfect_for_pcm(self, probe_pcm):
        from audio.audio_route_plan import AudioRoutePlan
        route = AudioRoutePlan(bitperfect_expected=True)
        factory = MagicMock()
        factory._build_bitperfect = MagicMock(return_value="bp-pipeline")
        factory._build_standard = MagicMock()

        result = _dispatch_build_for_uri(factory, "file:///test.flac", probe_pcm, route)

        factory._build_bitperfect.assert_called_once()
        assert result == "bp-pipeline"

    # ── 3. dsd_mode selection from profiles ──

    def test_dsd_mode_selection_dop_profile(self):
        from audio.output_profiles import get_profile
        prof = get_profile("dop_experimental")
        assert prof.dsd_mode == "dop"
        assert prof.preferred_backend == "alsa"
        assert prof.bitperfect is False

    def test_dsd_mode_selection_dsd_to_pcm_profile(self):
        from audio.output_profiles import get_profile
        prof = get_profile("dsd_to_pcm")
        assert prof.dsd_mode == "pcm"

    def test_dsd_mode_selection_mpd_native(self):
        from audio.output_profiles import get_profile
        prof = get_profile("michi_dsd_mpd")
        assert prof.dsd_mode == "native"
        assert prof.preferred_backend == "mpd"

    def test_dsd_mode_selection_standard_has_no_dsd(self):
        from audio.output_profiles import get_profile
        prof = get_profile("standard")
        assert prof.dsd_mode == ""

    @pytest.mark.skip(reason="needs real engine")
    def test_dsd_mode_selection_dop_route_plan(self, probe_dsd):
        from audio.dac_manager import DacManager
        from audio.audio_route_plan import AudioRoutePlan
        from audio.output_profiles import get_profile

        mgr = DacManager(MagicMock())
        dev = MagicMock()
        dev.supports_dop = True
        profile = get_profile("dop_experimental")
        plan = AudioRoutePlan()

        result = mgr._plan_dsd(probe_dsd, profile, dev, plan)

        assert result.dsd_mode == "dop"
        assert result.use_audioconvert is False
        assert result.use_audioresample is False

    @pytest.mark.skip(reason="needs real engine")
    def test_dsd_mode_selection_dop_route_plan_pcm_fallback(self, probe_dsd):
        from audio.dac_manager import DacManager
        from audio.audio_route_plan import AudioRoutePlan
        from audio.output_profiles import get_profile

        mgr = DacManager(MagicMock())
        dev = MagicMock()
        dev.supports_dop = False
        profile = get_profile("dop_experimental")
        plan = AudioRoutePlan()

        result = mgr._plan_dsd(probe_dsd, profile, dev, plan)

        assert result.dsd_mode == ""
        assert "DoP no soportado" in (result.warnings[0] if result.warnings else "")
        assert result.fallback_suggestion == "dsd_to_pcm"

    # ── 4. PCM fallback when DoP unavailable ──

    @pytest.mark.skip(reason="needs real engine")
    def test_pcm_fallback_dop_not_supported(self, probe_dsd):
        from audio.dac_manager import DacManager
        from audio.audio_route_plan import AudioRoutePlan
        from audio.output_profiles import get_profile

        mgr = DacManager(MagicMock())
        dev = MagicMock()
        dev.supports_dop = False
        profile = get_profile("dop_experimental")
        plan = AudioRoutePlan()

        result = mgr._plan_dsd(probe_dsd, profile, dev, plan)

        assert result.dsd_mode == ""
        assert "DoP no soportado" in (result.warnings[0] if result.warnings else "")
        assert result.fallback_suggestion == "dsd_to_pcm"

    @pytest.mark.skip(reason="needs real engine")
    def test_pcm_fallback_no_device(self, probe_dsd):
        from audio.dac_manager import DacManager
        from audio.audio_route_plan import AudioRoutePlan
        from audio.output_profiles import get_profile

        mgr = DacManager(MagicMock())
        profile = get_profile("dop_experimental")
        plan = AudioRoutePlan()

        result = mgr._plan_dsd(probe_dsd, profile, None, plan)

        assert result.dsd_mode == ""
        assert result.fallback_suggestion == "dsd_to_pcm"

    def test_pcm_fallback_dop_env_var_not_set(self, probe_dsd):
        from audio.audio_route_plan import AudioRoutePlan
        from audio.pipeline_factory import PipelineFactory

        route = AudioRoutePlan(dsd_mode="dop")
        factory = PipelineFactory()

        with patch.dict("os.environ", clear=True):
            result = factory._build_dop("file:///test.dsf", probe_dsd, route)

        assert result is None

    def test_pcm_fallback_dop_env_var_set(self, probe_dsd):
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        from audio.audio_route_plan import AudioRoutePlan
        from audio.pipeline_factory import PipelineFactory

        route = AudioRoutePlan(dsd_mode="dop")
        factory = PipelineFactory()

        with patch.dict("os.environ", {"MICHI_DOP_EXPERIMENTAL": "1"}):
            result = factory._build_dop("file:///test.dsf", probe_dsd, route)

        assert result is not None
        assert isinstance(result, Gst.Pipeline)

    @pytest.mark.skip(reason="needs real engine")
    def test_pcm_fallback_profile_selects_dsd_to_pcm_on_device_check(self, probe_dsd):
        from audio.audio_route_plan import AudioRoutePlan
        from audio.output_profiles import get_profile
        from audio.dac_manager import DacManager

        mgr = DacManager(MagicMock())
        dev = MagicMock()
        dev.supports_dop = False
        fallback_profile = get_profile("dsd_to_pcm")
        plan = AudioRoutePlan()

        result = mgr._plan_dsd(probe_dsd, fallback_profile, dev, plan)

        assert result.dsd_mode == "pcm"
        assert result.use_audioconvert is True
        assert result.use_audioresample is True
