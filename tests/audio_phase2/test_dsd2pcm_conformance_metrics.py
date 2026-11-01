"""AP2-F10 C7 — the tone oracle must not bias the measured amplitude.

The corpus tones are not FFT-bin centred at the 88.2 kHz target rate. A peak-bin
amplitude read from a Hann-windowed spectrum therefore under-reads the tone by
the window's scalloping loss (up to ~0.8 dB at 20 kHz). The §274.4 magnitude
criterion must be measured with an unbiased projection, otherwise a perfectly
flat decoder is reported as failing.
"""

from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from tools.audio_phase2.dsd2pcm_conformance import _tone_metrics  # noqa: E402


def _stereo_sine(
    frequency_hz: int,
    *,
    rate: int = 88_200,
    frames: int = 3_200,
    amplitude: float = 0.5,
) -> bytes:
    index = np.arange(frames)
    tone = amplitude * np.sin(2.0 * math.pi * frequency_hz * index / rate)
    interleaved = np.stack([tone, tone], axis=1).astype("<f4")
    return interleaved.tobytes()


@pytest.mark.parametrize("frequency_hz", [1_000, 10_000, 20_000])
def test_unbiased_projection_recovers_off_bin_tone_amplitude(
    frequency_hz: int,
) -> None:
    metrics = _tone_metrics(
        _stereo_sine(frequency_hz), channels=2, rate=88_200, expected_hz=frequency_hz
    )
    # A pure digital sine must measure at its analytic amplitude irrespective of
    # whether its frequency lands on an FFT bin.
    assert abs(metrics["tone_gain_error_db"]) <= 0.01


def test_projection_keeps_the_measured_frequency_near_the_tone() -> None:
    metrics = _tone_metrics(
        _stereo_sine(1_000), channels=2, rate=88_200, expected_hz=1_000
    )
    assert abs(metrics["tone_frequency_hz"] - 1_000.0) <= 20.0


def test_dc_offset_is_linear_and_dc_gain_is_not_measured() -> None:
    metrics = _tone_metrics(
        _stereo_sine(1_000, amplitude=0.01),
        channels=2,
        rate=88_200,
        expected_hz=1_000,
    )
    assert abs(metrics["dc_offset"]) < 1e-4
    assert metrics["dc_gain_error_db"] is None
    assert metrics["dc_gain_status"] == "NOT_MEASURED"
    assert "no DC stimulus" in metrics["dc_gain_reason"]


def test_inter_channel_latency_detects_a_one_sample_delay() -> None:
    frames = 3_200
    index = np.arange(frames)
    left = 0.5 * np.sin(2.0 * math.pi * 1_000 * index / 88_200)
    right = np.roll(left, 1)
    raw = np.stack([left, right], axis=1).astype("<f4").tobytes()
    metrics = _tone_metrics(raw, channels=2, rate=88_200, expected_hz=1_000)
    assert abs(metrics["inter_channel_latency_samples"]) == 1


def test_non_finite_and_clipping_samples_are_counted() -> None:
    frames = 64
    left = np.zeros(frames)
    right = np.zeros(frames)
    left[0] = math.nan
    right[0] = math.inf
    left[1] = 1.0
    right[1] = -1.0
    raw = np.stack([left, right], axis=1).astype("<f4").tobytes()
    metrics = _tone_metrics(raw, channels=2, rate=88_200, expected_hz=1_000)
    assert metrics["nan_inf"] == 2
    assert metrics["clipping_samples"] == 2
