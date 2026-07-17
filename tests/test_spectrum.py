"""Tests for spectrum analysis functions.

Focuses on pure data flow (push_fft mapping). Widget painting tests
would require qapp/qtbot.
"""
import numpy as np
import pytest
import pytest
pytest.skip("audio.spectrum module removed", allow_module_level=True)

from audio.spectrum import (
    SpectrumWidget, SPEC_BANDS, SPEC_MIN_HZ, SPEC_MAX_HZ, SPEC_FREQS,
    SPECTRUM_PALETTE,
)


class TestSpectrumConstants:
    def test_spec_bands_count(self):
        assert SPEC_BANDS == 60

    def test_spec_min_hz(self):
        assert SPEC_MIN_HZ == 20

    def test_spec_max_hz(self):
        assert SPEC_MAX_HZ == 20000

    def test_spec_freqs_length(self):
        assert len(SPEC_FREQS) == SPEC_BANDS

    def test_spec_freqs_log_spaced(self):
        ratios = SPEC_FREQS[1:] / SPEC_FREQS[:-1]
        assert np.allclose(ratios, ratios[0], rtol=1e-4)

    def test_spec_freqs_range(self):
        assert SPEC_FREQS[0] == pytest.approx(20.0, abs=1)
        assert SPEC_FREQS[-1] == pytest.approx(20000.0, abs=500)

    def test_palette_length(self):
        assert len(SPECTRUM_PALETTE) == 20

    def test_palette_all_qcolor(self):
        from PySide6.QtGui import QColor
        assert all(isinstance(c, QColor) for c in SPECTRUM_PALETTE)


class TestSpectrumPushFft:
    def test_push_sine_fft(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        t = np.linspace(0, 1, sr, endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t)
        fft_data = np.fft.rfft(signal)
        w.push_fft(fft_data, sr)
        assert len(w._data) == SPEC_BANDS
        assert np.all(w._data >= 0.0)
        assert np.all(w._data <= 1.0)

    def test_push_silence(self, qapp):
        w = SpectrumWidget()
        fft_data = np.zeros(1024, dtype=np.complex128)
        w.push_fft(fft_data)
        assert np.all(w._data >= 0.0)

    def test_too_short_fft(self, qapp):
        w = SpectrumWidget()
        w.push_fft(np.array([1.0]))
        assert np.allclose(w._data, 0.0)

    def test_empty_fft(self, qapp):
        w = SpectrumWidget()
        w.push_fft(np.array([]))
        assert np.allclose(w._data, 0.0)

    def test_fft_with_dc_component(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        signal = np.ones(sr) * 0.5
        fft_data = np.fft.rfft(signal)
        w.push_fft(fft_data, sr)
        assert np.all(w._data >= 0.0)

    def test_fft_with_noise(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        np.random.seed(0)
        noise = np.random.randn(sr) * 0.1
        fft_data = np.fft.rfft(noise)
        w.push_fft(fft_data, sr)
        assert np.any(w._data > 0.1)

    def test_multiple_pushes_smoothing(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        t = np.linspace(0, 1, sr, endpoint=False)
        for freq in [220, 440, 880]:
            signal = np.sin(2 * np.pi * freq * t) * 0.5
            fft_data = np.fft.rfft(signal)
            w.push_fft(fft_data, sr)
        assert len(w._data) == SPEC_BANDS

    def test_push_preserves_peak(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        t = np.linspace(0, 1, sr, endpoint=False)
        signal = np.sin(2 * np.pi * 1000 * t)
        fft_data = np.fft.rfft(signal)
        w.push_fft(fft_data, sr)
        assert np.any(w._peak > 0)

    def test_repeated_silence_decays(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        t = np.linspace(0, 0.1, int(sr * 0.1))
        signal = np.sin(2 * np.pi * 440 * t)
        fft_data = np.fft.rfft(signal)
        w.push_fft(fft_data, sr)
        after_push = w._data.copy()
        w.push_fft(np.zeros(1024), sr)
        assert np.any(w._data <= after_push + 0.01) or np.all(w._data > 0)

    def test_push_with_different_sample_rates(self, qapp):
        w = SpectrumWidget()
        for sr in [22050, 44100, 48000, 96000]:
            signal = np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, int(sr * 0.1)))
            fft_data = np.fft.rfft(signal)
            w.push_fft(fft_data, sr)
            assert np.any(w._data > 0.2)

    def test_normalization_range(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr, endpoint=False))
        fft_data = np.fft.rfft(signal) * 0.01
        w.push_fft(fft_data, sr)
        assert np.all(w._data >= 0.0)
        assert np.all(w._data <= 1.0)

    def test_data_stays_in_range_after_multiple_pushes(self, qapp):
        w = SpectrumWidget()
        sr = 44100
        for _ in range(5):
            noise = np.random.randn(4096) * 0.05
            fft_data = np.fft.rfft(noise)
            w.push_fft(fft_data, sr)
        assert np.all(w._data >= 0.0) and np.all(w._data <= 1.0)


class TestSpectrumMode:
    def test_default_mode(self, qapp):
        w = SpectrumWidget()
        assert w._mode == "bars"

    def test_set_mode(self, qapp):
        w = SpectrumWidget()
        w.set_mode("line")
        assert w._mode == "line"
        w.set_mode("both")
        assert w._mode == "both"
        w.set_mode("bars")
        assert w._mode == "bars"

    def test_image_mode(self, qapp):
        w = SpectrumWidget()
        w.set_mode("line")
        w.push_fft(np.ones(1024, dtype=np.complex128))
        assert w._mode == "line"

    def test_initial_decay_values(self, qapp):
        w = SpectrumWidget()
        assert w._decay == 0.85
        assert w._peak_decay == 0.95

    def test_minimum_height(self, qapp):
        w = SpectrumWidget()
        assert w.minimumHeight() == 120
