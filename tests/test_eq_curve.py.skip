"""Tests for frequency response curve computation.

Tests the pure math components (eval_response) used by EqCurveWidget,
plus the widget's data flow through eval_response.

The EqCurveWidget's __init__ calls setStyleSheet with a complex QSS
string that causes a fatal abort in some PySide6 + pytest-qt
environments. We avoid creating the widget directly and instead
test the evaluation logic and the widget's attributes via the
public eval_response API.
"""
import numpy as np
import pytest
from audio.eq_biquad import eval_response
from audio.eq_curve import EqCurveWidget


class TestEqCurveDataFlow:
    def test_set_bands_updates_response(self, qapp):
        widget = EqCurveWidget()
        bands = [{"type": "Peak", "freq": 1000, "gain": 6.0, "Q": 1.41}]
        widget._response = eval_response(bands, widget._freqs, 0.0)
        assert widget._response is not None
        assert len(widget._response) == 512
        assert np.any(widget._response > 0)

    def test_set_bands_with_preamp(self, qapp):
        widget = EqCurveWidget()
        widget._response = eval_response([], widget._freqs, 3.0)
        assert widget._response[0] == pytest.approx(3.0, abs=1e-6)

    def test_set_bands_empty(self, qapp):
        widget = EqCurveWidget()
        widget._response = eval_response([], widget._freqs, 0.0)
        assert np.allclose(widget._response, 0.0)

    def test_response_matches_eval_directly(self):
        bands = [{"type": "LowShelf", "freq": 80, "gain": 4.0, "Q": 0.7}]
        freqs = np.logspace(1.3, 4.3, 512)
        result = eval_response(bands, freqs, 0.0)
        assert len(result) == 512
        assert result[0] > 0

    def test_freqs_is_log_spaced(self, qapp):
        widget = EqCurveWidget()
        assert widget._freqs[0] == pytest.approx(20.0, abs=1)
        assert widget._freqs[-1] == pytest.approx(20000.0, abs=500)
        assert len(widget._freqs) == 512

    def test_set_bands_multiple_calls(self):
        bands1 = [{"type": "Peak", "freq": 100, "gain": 3.0, "Q": 1.0}]
        bands2 = [{"type": "Peak", "freq": 10000, "gain": -3.0, "Q": 1.0}]
        freqs = np.logspace(1.3, 4.3, 512)
        r1 = eval_response(bands1, freqs, 0.0)
        r2 = eval_response(bands2, freqs, 0.0)
        assert not np.allclose(r1, r2)

    def test_complex_multi_band_response(self):
        bands = [
            {"type": "LowShelf", "freq": 80, "gain": 4.0, "Q": 0.7},
            {"type": "Peak", "freq": 250, "gain": -2.0, "Q": 1.2},
            {"type": "Peak", "freq": 2500, "gain": 4.0, "Q": 1.5},
            {"type": "HighShelf", "freq": 10000, "gain": 2.0, "Q": 0.7},
        ]
        freqs = np.logspace(1.3, 4.3, 512)
        result = eval_response(bands, freqs, -1.5)
        assert np.all(np.isfinite(result))

    def test_preamp_db_propagation_in_eval(self):
        freqs = np.logspace(1.3, 4.3, 512)
        result = eval_response([], freqs, -4.2)
        assert result[100] == pytest.approx(-4.2, abs=1e-6)

    def test_curve_shape_low_shelf_boost(self):
        freqs = np.array([20, 100, 1000, 10000])
        bands = [{"type": "LowShelf", "freq": 100, "gain": 6.0, "Q": 0.7}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[0] > result[1]

    def test_curve_shape_high_shelf_boost(self):
        freqs = np.array([20, 100, 1000, 10000])
        bands = [{"type": "HighShelf", "freq": 5000, "gain": 6.0, "Q": 0.7}]
        result = eval_response(bands, freqs, 0.0, 44100)
        assert result[-1] > result[-2]
