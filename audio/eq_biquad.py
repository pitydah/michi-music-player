# -*- coding: utf-8 -*-
"""RBJ Audio EQ Cookbook — biquad filter coefficient calculator."""

from __future__ import annotations

from typing import Any

import numpy as np


def _prewarp(freq: float, fs: float = 44100.0) -> float:
    """Pre-warp frequency for bilinear transform."""
    if freq >= fs / 2:
        freq = fs / 2 - 1
    return np.tan(np.pi * freq / fs)


def peak_eq(freq: float, gain_db: float, Q: float = 1.41,
            fs: float = 44100.0) -> tuple[float, ...]:
    """Peak (bell) filter."""
    A = np.power(10.0, gain_db / 40.0)
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)

    b0 = 1.0 + alpha * A
    b1 = -2.0 * np.cos(w0)
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * np.cos(w0)
    a2 = 1.0 - alpha / A

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def low_shelf(freq: float, gain_db: float, Q: float = 0.707,
              fs: float = 44100.0) -> tuple[float, ...]:
    """Low shelf filter."""
    A = np.power(10.0, gain_db / 40.0)
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)
    sqrtA = np.sqrt(A)

    b0 = A * ((A + 1.0) - (A - 1.0) * cos + 2.0 * sqrtA * alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos)
    b2 = A * ((A + 1.0) - (A - 1.0) * cos - 2.0 * sqrtA * alpha)
    a0 = (A + 1.0) + (A - 1.0) * cos + 2.0 * sqrtA * alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos)
    a2 = (A + 1.0) + (A - 1.0) * cos - 2.0 * sqrtA * alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def high_shelf(freq: float, gain_db: float, Q: float = 0.707,
               fs: float = 44100.0) -> tuple[float, ...]:
    """High shelf filter."""
    A = np.power(10.0, gain_db / 40.0)
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)
    sqrtA = np.sqrt(A)

    b0 = A * ((A + 1.0) + (A - 1.0) * cos + 2.0 * sqrtA * alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos - 2.0 * sqrtA * alpha)
    a0 = (A + 1.0) - (A - 1.0) * cos + 2.0 * sqrtA * alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos)
    a2 = (A + 1.0) - (A - 1.0) * cos - 2.0 * sqrtA * alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def low_pass(freq: float, Q: float = 0.707,
             fs: float = 44100.0) -> tuple[float, ...]:
    """Low pass filter."""
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)

    b0 = (1.0 - cos) / 2.0
    b1 = 1.0 - cos
    b2 = (1.0 - cos) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos
    a2 = 1.0 - alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def high_pass(freq: float, Q: float = 0.707,
              fs: float = 44100.0) -> tuple[float, ...]:
    """High pass filter."""
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)

    b0 = (1.0 + cos) / 2.0
    b1 = -(1.0 + cos)
    b2 = (1.0 + cos) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos
    a2 = 1.0 - alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def notch(freq: float, Q: float = 10.0,
          fs: float = 44100.0) -> tuple[float, ...]:
    """Notch (band reject) filter."""
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)

    b0 = 1.0
    b1 = -2.0 * cos
    b2 = 1.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos
    a2 = 1.0 - alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


def band_pass(freq: float, Q: float = 1.0,
              fs: float = 44100.0) -> tuple[float, ...]:
    """Band pass filter (constant skirt gain, peak gain = Q)."""
    w0 = 2.0 * np.pi * freq / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos = np.cos(w0)

    b0 = Q * alpha
    b1 = 0.0
    b2 = -Q * alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * cos
    a2 = 1.0 - alpha

    return (float(b0), float(b1), float(b2), float(a0), float(a1), float(a2))


# ── Generic dispatch ──

FILTER_TYPES = {
    "Peak":       peak_eq,
    "LowShelf":   low_shelf,
    "HighShelf":  high_shelf,
    "LowPass":    low_pass,
    "HighPass":   high_pass,
    "Notch":      notch,
    "BandPass":   band_pass,
}

FILTER_LABELS = {
    "Peak":       "Peak (Bell)",
    "LowShelf":   "Low Shelf",
    "HighShelf":  "High Shelf",
    "LowPass":    "Low Pass",
    "HighPass":   "High Pass",
    "Notch":      "Notch",
    "BandPass":   "Band Pass",
}


def compute_biquad(f_type: str, freq: float, gain_db: float, Q: float,
                   fs: float = 44100.0) -> tuple[float, ...]:
    """Compute biquad coefficients for a given filter type."""
    fn = FILTER_TYPES.get(f_type)
    if fn is None:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # passthrough

    if f_type in ("LowPass", "HighPass", "Notch", "BandPass"):
        return fn(freq, Q, fs)  # type: ignore
    return fn(freq, gain_db, Q, fs)  # type: ignore


def eval_response(bands: list[dict], freqs: np.ndarray, preamp_db: float = 0.0,
                  fs: float = 44100.0) -> np.ndarray:
    """Evaluate combined frequency response of all bands + preamp, in dB."""
    if not bands:
        return np.full_like(freqs, float(preamp_db), dtype=np.float64)

    H = np.ones(len(freqs), dtype=np.complex128) * np.power(10.0, preamp_db / 20.0)

    for band in bands:
        coefs = compute_biquad(
            band["type"], band["freq"], band.get("gain", 0.0),
            band.get("Q", 1.41), fs)
        b0, b1, b2, a0, a1, a2 = coefs
        # Evaluate biquad at each frequency
        w = 2.0 * np.pi * freqs / fs
        z = np.exp(-1j * w)
        num = b0 + b1 * z + b2 * z * z
        den = a0 + a1 * z + a2 * z * z
        H *= num / den

    return 20.0 * np.log10(np.abs(H) + 1e-12)
