"""Tests for RBJ biquad filter coefficient computation."""
import numpy as np
import pytest
from audio.eq_biquad import (
    _prewarp, peak_eq, low_shelf, high_shelf, low_pass, high_pass,
    notch, band_pass, compute_biquad, eval_response, FILTER_TYPES, FILTER_LABELS,
)


class TestPrewarp:
    def test_basic_prewarp(self):
        result = _prewarp(1000.0, 44100.0)
        assert 0.07 < result < 0.08

    def test_prewarp_clip_nyquist(self):
        result = _prewarp(30000.0, 44100.0)
        expected = np.tan(np.pi * (22049.0) / 44100.0)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_prewarp_dc(self):
        result = _prewarp(0.0, 44100.0)
        assert result == pytest.approx(0.0, abs=1e-12)

    def test_prewarp_different_fs(self):
        result = _prewarp(1000.0, 96000.0)
        assert 0.03 < result < 0.04


class TestPeakEq:
    def test_zero_gain_symmetric(self):
        b0, b1, b2, a0, a1, a2 = peak_eq(1000, 0.0, 1.41, 44100)
        assert b0 == pytest.approx(a0, abs=1e-3)
        assert b2 == pytest.approx(a2, abs=1e-3)

    def test_positive_gain(self):
        b0, b1, b2, a0, a1, a2 = peak_eq(1000, 6.0, 1.41, 44100)
        assert b0 > a0
        assert b2 < a2

    def test_negative_gain(self):
        b0, b1, b2, a0, a1, a2 = peak_eq(1000, -6.0, 1.41, 44100)
        assert b0 < a0

    def test_returns_six_floats(self):
        coefs = peak_eq(1000, 3.0, 1.0, 44100)
        assert len(coefs) == 6
        assert all(isinstance(c, float) for c in coefs)

    def test_different_q(self):
        b0_q1, *_ = peak_eq(1000, 6.0, 1.0, 44100)
        b0_q2, *_ = peak_eq(1000, 6.0, 2.0, 44100)
        assert b0_q1 != pytest.approx(b0_q2, rel=1e-3)

    def test_extreme_freq_low(self):
        coefs = peak_eq(20, 12.0, 0.5, 44100)
        assert all(np.isfinite(c) for c in coefs)

    def test_extreme_freq_high(self):
        coefs = peak_eq(20000, 12.0, 0.5, 44100)
        assert all(np.isfinite(c) for c in coefs)

    def test_dc_gain_boost(self):
        b0, b1, b2, a0, a1, a2 = peak_eq(100, 10.0, 0.7, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain == pytest.approx(1.0, abs=0.01)

    def test_max_boost_symmetry(self):
        b0, b1, b2, a0, a1, a2 = peak_eq(1000, 10.0, 1.0, 44100)
        b0n, b1n, b2n, a0n, a1n, a2n = peak_eq(1000, -10.0, 1.0, 44100)
        assert b0 == pytest.approx(a0n, rel=1e-6)
        assert b2 == pytest.approx(a2n, rel=1e-6)

    def test_near_dc_freq(self):
        coefs = peak_eq(1, 6.0, 1.0, 44100)
        assert all(np.isfinite(c) for c in coefs)


class TestLowShelf:
    def test_zero_gain(self):
        b0, b1, b2, a0, a1, a2 = low_shelf(100, 0.0, 0.707, 44100)
        assert b0 == pytest.approx(a0, abs=1e-3)

    def test_boost_dc_gain(self):
        b0, b1, b2, a0, a1, a2 = low_shelf(100, 6.0, 0.707, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        expected = 10.0 ** (6.0 / 20.0)
        assert dc_gain == pytest.approx(expected, rel=0.1)

    def test_cut_high_freq_gain(self):
        b0, b1, b2, a0, a1, a2 = low_shelf(100, -6.0, 0.707, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        assert hf_gain == pytest.approx(1.0, abs=0.05)

    def test_returns_six_floats(self):
        coefs = low_shelf(100, 3.0, 0.707, 44100)
        assert len(coefs) == 6
        assert all(isinstance(c, float) for c in coefs)

    def test_extreme_q(self):
        coefs = low_shelf(100, 6.0, 0.1, 44100)
        assert all(np.isfinite(c) for c in coefs)


class TestHighShelf:
    def test_zero_gain(self):
        b0, b1, b2, a0, a1, a2 = high_shelf(5000, 0.0, 0.707, 44100)
        assert b0 == pytest.approx(a0, abs=1e-3)

    def test_boost_hf_gain(self):
        b0, b1, b2, a0, a1, a2 = high_shelf(5000, 6.0, 0.707, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        expected = 10.0 ** (6.0 / 20.0)
        assert hf_gain == pytest.approx(expected, rel=0.1)

    def test_cut_dc_gain(self):
        b0, b1, b2, a0, a1, a2 = high_shelf(5000, -6.0, 0.707, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain == pytest.approx(1.0, abs=0.05)

    def test_returns_six_floats(self):
        coefs = high_shelf(5000, 3.0, 0.707, 44100)
        assert len(coefs) == 6
        assert all(isinstance(c, float) for c in coefs)


class TestLowPass:
    def test_dc_gain_unity(self):
        b0, b1, b2, a0, a1, a2 = low_pass(1000, 0.707, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain == pytest.approx(1.0, rel=1e-6)

    def test_high_freq_attenuation(self):
        b0, b1, b2, a0, a1, a2 = low_pass(1000, 0.707, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        assert hf_gain < 0.1

    def test_cutoff_response(self):
        b0, b1, b2, a0, a1, a2 = low_pass(1000, 0.707, 44100)
        w0 = 2.0 * np.pi * 1000 / 44100
        z = np.exp(-1j * w0)
        num = b0 + b1 * z + b2 * z * z
        den = a0 + a1 * z + a2 * z * z
        gain = np.abs(num / den)
        assert gain == pytest.approx(np.sqrt(0.5), rel=0.15)

    def test_returns_six_floats(self):
        coefs = low_pass(1000, 0.707, 44100)
        assert len(coefs) == 6
        assert all(isinstance(c, float) for c in coefs)

    def test_butterworth_q(self):
        coefs = low_pass(1000, 0.7071, 44100)
        assert all(np.isfinite(c) for c in coefs)


class TestHighPass:
    def test_hf_gain_unity(self):
        b0, b1, b2, a0, a1, a2 = high_pass(1000, 0.707, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        assert hf_gain == pytest.approx(1.0, rel=1e-6)

    def test_dc_rejection(self):
        b0, b1, b2, a0, a1, a2 = high_pass(1000, 0.707, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain < 0.1

    def test_cutoff_response(self):
        b0, b1, b2, a0, a1, a2 = high_pass(1000, 0.707, 44100)
        w0 = 2.0 * np.pi * 1000 / 44100
        z = np.exp(-1j * w0)
        num = b0 + b1 * z + b2 * z * z
        den = a0 + a1 * z + a2 * z * z
        gain = np.abs(num / den)
        assert gain == pytest.approx(np.sqrt(0.5), rel=0.15)

    def test_returns_six_floats(self):
        coefs = high_pass(1000, 0.707, 44100)
        assert len(coefs) == 6
        assert all(isinstance(c, float) for c in coefs)


class TestNotch:
    def test_dc_gain_unity(self):
        b0, b1, b2, a0, a1, a2 = notch(1000, 10.0, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain == pytest.approx(1.0, rel=1e-6)

    def test_hf_gain_unity(self):
        b0, b1, b2, a0, a1, a2 = notch(1000, 10.0, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        assert hf_gain == pytest.approx(1.0, rel=1e-6)

    def test_notch_attenuation(self):
        b0, b1, b2, a0, a1, a2 = notch(1000, 10.0, 44100)
        w0 = 2.0 * np.pi * 1000 / 44100
        z = np.exp(-1j * w0)
        num = b0 + b1 * z + b2 * z * z
        den = a0 + a1 * z + a2 * z * z
        gain = np.abs(num / den)
        assert gain < 0.15

    def test_returns_six_floats(self):
        coefs = notch(1000, 10.0, 44100)
        assert len(coefs) == 6

    def test_b0_b2_are_one(self):
        b0, b1, b2, a0, a1, a2 = notch(1000, 10.0, 44100)
        assert b0 == 1.0
        assert b2 == 1.0


class TestBandPass:
    def test_dc_zero(self):
        b0, b1, b2, a0, a1, a2 = band_pass(1000, 1.0, 44100)
        dc_gain = (b0 + b1 + b2) / (a0 + a1 + a2)
        assert dc_gain == pytest.approx(0.0, abs=1e-12)

    def test_hf_zero(self):
        b0, b1, b2, a0, a1, a2 = band_pass(1000, 1.0, 44100)
        hf_gain = (b0 - b1 + b2) / (a0 - a1 + a2)
        assert hf_gain == pytest.approx(0.0, abs=1e-12)

    def test_peak_gain(self):
        b0, b1, b2, a0, a1, a2 = band_pass(1000, 1.0, 44100)
        w0 = 2.0 * np.pi * 1000 / 44100
        z = np.exp(-1j * w0)
        num = b0 + b1 * z + b2 * z * z
        den = a0 + a1 * z + a2 * z * z
        gain = np.abs(num / den)
        assert gain == pytest.approx(1.0, rel=0.15)

    def test_returns_six_floats(self):
        coefs = band_pass(1000, 2.0, 44100)
        assert len(coefs) == 6

    def test_b1_zero(self):
        _, b1, _, _, _, _ = band_pass(1000, 2.0, 44100)
        assert b1 == 0.0


class TestComputeBiquad:
    def test_invalid_type_returns_passthrough(self):
        coefs = compute_biquad("InvalidType", 1000, 0.0, 1.0, 44100)
        assert coefs == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def test_empty_string_type(self):
        coefs = compute_biquad("", 1000, 0.0, 1.0, 44100)
        assert coefs == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def test_low_pass_dispatch(self):
        coefs = compute_biquad("LowPass", 1000, 0.0, 0.707, 44100)
        expected = low_pass(1000, 0.707, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_high_pass_dispatch(self):
        coefs = compute_biquad("HighPass", 1000, 0.0, 0.707, 44100)
        expected = high_pass(1000, 0.707, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_peak_dispatch(self):
        coefs = compute_biquad("Peak", 1000, 3.0, 1.41, 44100)
        expected = peak_eq(1000, 3.0, 1.41, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_notch_dispatch(self):
        coefs = compute_biquad("Notch", 1000, 0.0, 10.0, 44100)
        expected = notch(1000, 10.0, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_band_pass_dispatch(self):
        coefs = compute_biquad("BandPass", 1000, 0.0, 1.0, 44100)
        expected = band_pass(1000, 1.0, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_low_shelf_dispatch(self):
        coefs = compute_biquad("LowShelf", 100, 4.0, 0.707, 44100)
        expected = low_shelf(100, 4.0, 0.707, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)

    def test_high_shelf_dispatch(self):
        coefs = compute_biquad("HighShelf", 5000, 3.0, 0.707, 44100)
        expected = high_shelf(5000, 3.0, 0.707, 44100)
        assert coefs == pytest.approx(expected, rel=1e-6)


class TestEvalResponse:
    def test_empty_bands_returns_preamp(self):
        freqs = np.array([100, 1000, 10000])
        result = eval_response([], freqs, -3.0, 44100)
        assert result == pytest.approx(np.full(3, -3.0), abs=1e-6)

    def test_empty_bands_zero_preamp(self):
        freqs = np.array([100, 1000, 10000])
        result = eval_response([], freqs, 0.0, 44100)
        assert result == pytest.approx(np.zeros(3), abs=1e-6)

    def test_single_peak_band(self):
        freqs = np.array([100, 1000, 10000])
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0, "Q": 1.41}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[1] > result[0]
        assert result[1] > result[2]

    def test_low_pass_response(self):
        freqs = np.array([50, 1000, 10000])
        bands = [{"type": "LowPass", "freq": 500, "gain": 0.0, "Q": 0.707}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] > result[1] > result[2]

    def test_high_pass_response(self):
        freqs = np.array([50, 1000, 10000])
        bands = [{"type": "HighPass", "freq": 500, "gain": 0.0, "Q": 0.707}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] < result[1] < result[2]

    def test_combined_bands(self):
        freqs = np.array([100, 1000])
        bands = [
            {"type": "Peak", "freq": 100, "gain": 3.0, "Q": 1.0},
            {"type": "Peak", "freq": 1000, "gain": -2.0, "Q": 1.0},
        ]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] > 0
        assert result[1] < 0

    def test_with_preamp(self):
        freqs = np.array([1000])
        bands = [{"type": "Peak", "freq": 1000, "gain": 3.0, "Q": 1.41}]
        result = eval_response(bands, freqs, 2.0, 44100)
        result_no_preamp = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] > result_no_preamp[0]

    def test_missing_gain_defaults_zero(self):
        freqs = np.array([1000])
        bands = [{"type": "Peak", "freq": 1000, "Q": 1.41}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] == pytest.approx(0.0, abs=0.1)

    def test_missing_Q_defaults(self):
        freqs = np.array([1000])
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert np.isfinite(result[0])

    def test_band_pass_shape(self):
        freqs = np.array([100, 1000, 10000])
        bands = [{"type": "BandPass", "freq": 1000, "gain": 0.0, "Q": 2.0}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[1] > result[0] and result[1] > result[2]

    def test_notch_shape(self):
        freqs = np.array([100, 1000, 10000])
        bands = [{"type": "Notch", "freq": 1000, "gain": 0.0, "Q": 10.0}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[1] < result[0] and result[1] < result[2]

    def test_different_sample_rate(self):
        freqs = np.array([100, 1000, 10000])
        bands = [{"type": "LowPass", "freq": 1000, "gain": 0.0, "Q": 0.707}]
        r44 = eval_response(bands, freqs, 0.0, 44100)
        r96 = eval_response(bands, freqs, 0.0, 96000)
        assert not np.allclose(r44, r96)

    def test_large_band_count_stability(self):
        bands = [{"type": "Peak", "freq": float(f), "gain": 3.0, "Q": 1.41}
                 for f in range(20, 20000, 200)]
        freqs = np.logspace(1.3, 4.3, 512)
        result = eval_response(bands, freqs, 0.0, 44100)
        assert np.all(np.isfinite(result))

    def test_log_freq_scale(self):
        freqs = np.logspace(1.3, 4.3, 512)
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0, "Q": 1.41}]
        result = eval_response(bands, freqs, 0.0, 44100)
        max_idx = np.argmax(result)
        peaks = freqs[max_idx]
        assert 800 <= peaks <= 1200

    def test_single_freq_point(self):
        result = eval_response([{"type": "Peak", "freq": 1000, "gain": 3.0, "Q": 1.41}],
                               np.array([1000.0]), 0.0, 44100)
        assert len(result) == 1
        assert np.isfinite(result[0])


class TestFilterTypeConstants:
    def test_filters_types_complete(self):
        assert set(FILTER_TYPES.keys()) == {
            "Peak", "LowShelf", "HighShelf", "LowPass", "HighPass", "Notch", "BandPass",
        }

    def test_filters_labels_complete(self):
        assert set(FILTER_LABELS.keys()) == set(FILTER_TYPES.keys())

    def test_all_labels_are_strings(self):
        assert all(isinstance(v, str) for v in FILTER_LABELS.values())
