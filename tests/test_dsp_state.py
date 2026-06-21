"""Tests for DspState module."""
from audio.dsp_state import DspState


class TestDspState:
    def test_default_inactive(self):
        dsp = DspState()
        assert dsp.is_dsp_active() is False

    def test_eq_active(self):
        dsp = DspState(eq_enabled=True, eq_mode="graphic")
        assert dsp.is_dsp_active() is True

    def test_replaygain_active(self):
        dsp = DspState(replaygain_enabled=True)
        assert dsp.is_dsp_active() is True

    def test_crossfade_active(self):
        dsp = DspState(crossfade_seconds=3)
        assert dsp.is_dsp_active() is True

    def test_spectrum_active(self):
        dsp = DspState(spectrum_enabled=True)
        assert dsp.is_dsp_active() is True

    def test_transmit_active(self):
        dsp = DspState(transmit_enabled=True)
        assert dsp.is_dsp_active() is True

    def test_all_inactive(self):
        dsp = DspState(
            eq_enabled=False, replaygain_enabled=False,
            crossfade_seconds=0, spectrum_enabled=False,
            transmit_enabled=False)
        assert dsp.is_dsp_active() is False

    def test_parametric_fields(self):
        bands = [{"type": "peaking", "frequency": 1000, "q": 0.7, "gain": 3.0,
                   "a0": 1.0, "a1": 0.0, "a2": 0.0,
                   "b0": 1.0, "b1": 0.0, "b2": 0.0}]
        dsp = DspState(eq_mode="parametric", eq_bands_parametric=bands,
                        eq_preamp_db=-2.0)
        assert dsp.eq_mode == "parametric"
        assert len(dsp.eq_bands_parametric) == 1
        assert dsp.eq_preamp_db == -2.0

    def test_replaygain_db_field(self):
        dsp = DspState(replaygain_enabled=True, replaygain_db=-4.5)
        assert dsp.replaygain_db == -4.5
