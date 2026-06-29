"""Tests for the spectral authenticator (fake hi-res detection)."""

from __future__ import annotations

import numpy as np
from core.audio_analysis.spectral_authenticator import (
    _compute_spectral_analysis,
    _hann_window,
    _verdict_from_metrics,
    analyse_spectral,
    can_analyse,
)


class TestSpectralAuthenticator:
    def test_hann_window_shape(self):
        w = _hann_window(512)
        assert len(w) == 512
        assert np.allclose(w[0], 0.0, atol=1e-6)
        assert np.allclose(w[-1], 0.0, atol=1e-6)
        assert w[256] > w[0]

    def test_compute_spectral_empty_samples(self):
        result = _compute_spectral_analysis(np.array([]), 44100)
        assert result == {}

    def test_compute_spectral_few_samples(self):
        result = _compute_spectral_analysis(np.array([0.0] * 100), 44100)
        assert result == {}

    def test_verdict_hires_coherent(self):
        metrics = {
            "spectral_rolloff_95": 50000.0,
            "spectral_rolloff_99": 60000.0,
            "energy_above_16k": 0.1,
            "energy_above_18k": 0.05,
            "energy_above_20k": 0.02,
        }
        verdict, label, _ = _verdict_from_metrics(metrics, 192000, 24)
        assert verdict == "HI_RES_COHERENT"
        assert "coherente" in label

    def test_verdict_suspicious_upsampling(self):
        metrics = {
            "spectral_rolloff_95": 12000.0,
            "spectral_rolloff_99": 18000.0,
            "energy_above_16k": 1e-8,
            "energy_above_18k": 1e-9,
            "energy_above_20k": 1e-10,
        }
        verdict, label, _ = _verdict_from_metrics(metrics, 192000, 24)
        assert verdict == "SUSPICIOUS_UPSAMPLING"
        assert "sospechoso" in label

    def test_verdict_lossless_coherent(self):
        metrics = {
            "spectral_rolloff_95": 18000.0,
            "spectral_rolloff_99": 20000.0,
            "energy_above_16k": 0.01,
            "energy_above_18k": 0.001,
            "energy_above_20k": 1e-8,
        }
        verdict, label, _ = _verdict_from_metrics(metrics, 44100, 16)
        assert verdict == "LOSSLESS_COHERENT"
        assert "coherente" in label

    def test_verdict_possible_lossy(self):
        metrics = {
            "spectral_rolloff_95": 8000.0,
            "spectral_rolloff_99": 14000.0,
            "energy_above_16k": 1e-10,
            "energy_above_18k": 1e-11,
            "energy_above_20k": 1e-12,
        }
        verdict, label, _ = _verdict_from_metrics(metrics, 44100, 16)
        assert verdict == "POSSIBLE_LOSSY_SOURCE"
        assert "pérdida" in label

    def test_verdict_inconclusive_unknown_sr(self):
        metrics = {
            "spectral_rolloff_95": 30000,
            "spectral_rolloff_99": 35000,
            "energy_above_16k": 0.002,
            "energy_above_18k": 0.0005,
            "energy_above_20k": 0.0001,
        }
        verdict, _label, _expl = _verdict_from_metrics(metrics, 64000, 24)
        assert verdict == "INCONCLUSIVE"

    def test_can_analyse_wav(self):
        assert can_analyse("song.wav")
        assert not can_analyse("song.flac")
        assert not can_analyse("song.mp3")

    def test_analyse_spectral_nonexistent_file(self):
        result = analyse_spectral("/nonexistent/file.wav")
        assert result["verdict"] == "ANALYSIS_ERROR"
        assert result["error"]

    def test_analyse_spectral_nonwav_file(self):
        result = analyse_spectral("/path/to/song.flac")
        assert result["verdict"] == "ANALYSIS_ERROR"
