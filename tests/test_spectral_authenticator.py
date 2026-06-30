"""Tests for the spectral authenticator (coherencia espectral Hi-Res)."""

from __future__ import annotations

import os
import tempfile
import wave

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
            "spectral_rolloff_95": 100000.0,
            "spectral_rolloff_99": 120000.0,
            "energy_above_16k": 0.1,
            "energy_above_18k": 0.05,
            "energy_above_20k": 0.02,
            "segments_analysed": 30,
        }
        verdict, label, _expl, conf = _verdict_from_metrics(metrics, 192000, 24)
        assert verdict == "HI_RES_COHERENT"
        assert "coherente" in label
        assert 0 < conf <= 1.0

    def test_verdict_suspicious_upsampling(self):
        metrics = {
            "spectral_rolloff_95": 12000.0,
            "spectral_rolloff_99": 18000.0,
            "energy_above_16k": 1e-8,
            "energy_above_18k": 1e-9,
            "energy_above_20k": 1e-10,
            "segments_analysed": 30,
        }
        verdict, label, _expl, conf = _verdict_from_metrics(metrics, 192000, 24)
        assert verdict == "SUSPICIOUS_UPSAMPLING"
        assert "sospechoso" in label
        assert 0 < conf <= 1.0

    def test_verdict_lossless_coherent(self):
        metrics = {
            "spectral_rolloff_95": 18000.0,
            "spectral_rolloff_99": 20000.0,
            "energy_above_16k": 0.01,
            "energy_above_18k": 0.001,
            "energy_above_20k": 1e-8,
            "segments_analysed": 30,
        }
        verdict, label, _expl, conf = _verdict_from_metrics(metrics, 44100, 16)
        assert verdict == "LOSSLESS_COHERENT"
        assert "coherente" in label
        assert 0 < conf <= 1.0

    def test_verdict_possible_lossy(self):
        metrics = {
            "spectral_rolloff_95": 8000.0,
            "spectral_rolloff_99": 14000.0,
            "energy_above_16k": 1e-10,
            "energy_above_18k": 1e-11,
            "energy_above_20k": 1e-12,
            "segments_analysed": 30,
        }
        verdict, label, _expl, conf = _verdict_from_metrics(metrics, 44100, 16)
        assert verdict == "POSSIBLE_LOSSY_SOURCE"
        assert "pérdida" in label
        assert 0 < conf <= 1.0

    def test_verdict_inconclusive_unknown_sr(self):
        metrics = {
            "spectral_rolloff_95": 30000,
            "spectral_rolloff_99": 35000,
            "energy_above_16k": 0.002,
            "energy_above_18k": 0.0005,
            "energy_above_20k": 0.0001,
        }
        verdict, _label, _expl, conf = _verdict_from_metrics(metrics, 64000, 24)
        assert verdict == "INCONCLUSIVE"
        assert 0 < conf <= 1.0

    def test_can_analyse_wav(self):
        assert can_analyse("song.wav")
        assert not can_analyse("song.mp3")

    def test_can_analyse_flac_requires_file(self):
        # FLAC requires the file to exist (unlike WAV which accepts nonexistent)
        import tempfile
        import shutil
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC\x00\x00\x00\x22\x10\x00\x10\x00")
            path = f.name
        try:
            import os
            if shutil.which("ffmpeg"):
                assert can_analyse(path) is True
            else:
                assert can_analyse(path) is False
        finally:
            os.unlink(path)

    def test_analyse_spectral_nonexistent_file(self):
        result = analyse_spectral("/nonexistent/file.wav")
        assert result["verdict"] == "ANALYSIS_ERROR"
        assert result["error"]

    def test_analyse_spectral_nonwav_file(self):
        result = analyse_spectral("/path/to/song.flac")
        assert result["verdict"] == "ANALYSIS_ERROR"

    def test_can_analyse_validates_wav_header(self):
        assert can_analyse("song.wav")
        assert not can_analyse("song.mp3")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVE")
            path = f.name
        try:
            assert can_analyse(path)
        finally:
            os.unlink(path)

    def test_can_analyse_rejects_non_wav_header(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"NOT A WAV FILE")
            path = f.name
        try:
            assert not can_analyse(path)
        finally:
            os.unlink(path)

    def test_analyse_32bit_pcm_no_crash(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 44100
            frames = int(sr * 1)
            data = np.array([0, 1000000, -1000000, 2147483647], dtype=np.int32)
            data = np.tile(data, frames // 4)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(4)
                wf.setframerate(sr)
                wf.writeframes(data.tobytes())
            result = analyse_spectral(path, sr, 32)
            assert result["verdict"] in (
                "LOSSLESS_COHERENT", "INCONCLUSIVE", "ANALYSIS_ERROR",
            )
        finally:
            os.unlink(path)

    def test_analyse_corrupt_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVE\x00\x00\x00\x00")
            path = f.name
        try:
            result = analyse_spectral(path, 44100, 16)
            assert result["verdict"] == "ANALYSIS_ERROR"
        finally:
            os.unlink(path)

    def test_metrics_contain_required_keys(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            sr = 44100
            frames = int(sr * 2)
            t = np.linspace(0, 2, frames, endpoint=False)
            tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(tone.tobytes())
            result = analyse_spectral(path, sr, 16)
            metrics = result.get("metrics", {})
            if result["verdict"] != "ANALYSIS_ERROR":
                for key in ("nyquist_hz", "effective_ceiling_hz",
                            "segments_analysed", "declared_sample_rate",
                            "declared_bit_depth"):
                    assert key in metrics, f"Missing metric: {key}"
                assert "confidence" in result
                assert 0 <= result["confidence"] <= 1.0
        finally:
            os.unlink(path)
