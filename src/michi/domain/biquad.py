"""Deterministic RBJ biquad coefficient math (AP2-F04, R11-G07).

Pure Python: ``math`` only, no NumPy, no I/O and no coefficient generation on
any future streaming thread. F05 consumes precompiled material; this module
computes immutable deterministic data and fails closed on unsafe inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from michi.domain.audio_processing import (
    GAINLESS_BIQUAD_TYPES,
    PEQ_GAIN_ENVELOPE_DB,
    BiquadType,
)


@dataclass(frozen=True, slots=True)
class BiquadCoefficients:
    """Normalized coefficients (a0 == 1 implied)."""

    b0: float
    b1: float
    b2: float
    a1: float
    a2: float


def _require_finite(name: str, value: float) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be finite")


def biquad_magnitude_db(
    coefficients: BiquadCoefficients,
    *,
    rate_hz: float,
    frequency_hz: float,
) -> float:
    """Magnitude of one normalized biquad at ``frequency_hz``, in dB.

    Pure evaluation of the same coefficients used by the graph compiler. This
    is a CALCULATED response, never a measurement of the audio signal.
    """
    _require_finite("rate_hz", rate_hz)
    _require_finite("frequency_hz", frequency_hz)
    if rate_hz <= 0:
        raise ValueError("rate_hz must be > 0")
    if frequency_hz < 0 or frequency_hz >= rate_hz / 2.0:
        raise ValueError("frequency_hz must be in [0, Nyquist)")
    omega = 2.0 * math.pi * frequency_hz / rate_hz
    cos1 = math.cos(omega)
    sin1 = math.sin(omega)
    cos2 = math.cos(2.0 * omega)
    sin2 = math.sin(2.0 * omega)
    num_real = coefficients.b0 + coefficients.b1 * cos1 + coefficients.b2 * cos2
    num_imag = -(coefficients.b1 * sin1 + coefficients.b2 * sin2)
    den_real = 1.0 + coefficients.a1 * cos1 + coefficients.a2 * cos2
    den_imag = -(coefficients.a1 * sin1 + coefficients.a2 * sin2)
    numerator = math.hypot(num_real, num_imag)
    denominator = math.hypot(den_real, den_imag)
    if denominator == 0.0 or not math.isfinite(numerator):
        raise ValueError("degenerate biquad response")
    magnitude = numerator / denominator
    if magnitude <= 0.0 or not math.isfinite(magnitude):
        raise ValueError("degenerate biquad magnitude")
    return 20.0 * math.log10(magnitude)


def biquad_coefficients(
    filter_type: BiquadType,
    *,
    rate_hz: float,
    frequency_hz: float,
    q: float,
    gain_db: float = 0.0,
) -> BiquadCoefficients:
    """RBJ Audio-EQ-Cookbook coefficients normalized by ``a0``.

    Raises ``ValueError`` for non-finite inputs, non-positive rates or Q, a
    frequency at/above Nyquist and gain on filter types without gain.
    """
    if not isinstance(filter_type, BiquadType):
        raise TypeError("filter_type must be a BiquadType")
    _require_finite("rate_hz", rate_hz)
    _require_finite("frequency_hz", frequency_hz)
    _require_finite("q", q)
    _require_finite("gain_db", gain_db)
    if rate_hz <= 0:
        raise ValueError("rate_hz must be > 0")
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    if frequency_hz >= rate_hz / 2.0:
        raise ValueError("frequency_hz must be below Nyquist")
    if q <= 0:
        raise ValueError("q must be > 0")
    if filter_type in GAINLESS_BIQUAD_TYPES and gain_db != 0.0:
        raise ValueError(f"{filter_type.value} has no gain parameter; gain must be 0")
    # Defensive: this utility is independently callable and must reject
    # out-of-envelope gains BEFORE 10 ** (gain_db / 40) can overflow.
    low, high = PEQ_GAIN_ENVELOPE_DB
    if not low <= gain_db <= high:
        raise ValueError(
            f"gain_db {gain_db} outside the canonical PEQ design envelope "
            f"[{low}, {high}] dB"
        )

    omega = 2.0 * math.pi * frequency_hz / rate_hz
    cos_omega = math.cos(omega)
    sin_omega = math.sin(omega)
    alpha = sin_omega / (2.0 * q)
    amplitude = 10.0 ** (gain_db / 40.0)
    sqrt_amplitude = math.sqrt(amplitude)

    if filter_type is BiquadType.PEAK:
        b0 = 1.0 + alpha * amplitude
        b1 = -2.0 * cos_omega
        b2 = 1.0 - alpha * amplitude
        a0 = 1.0 + alpha / amplitude
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha / amplitude
    elif filter_type is BiquadType.LOW_SHELF:
        b0 = amplitude * (
            (amplitude + 1.0)
            - (amplitude - 1.0) * cos_omega
            + 2.0 * sqrt_amplitude * alpha
        )
        b1 = 2.0 * amplitude * ((amplitude - 1.0) - (amplitude + 1.0) * cos_omega)
        b2 = amplitude * (
            (amplitude + 1.0)
            - (amplitude - 1.0) * cos_omega
            - 2.0 * sqrt_amplitude * alpha
        )
        a0 = (
            (amplitude + 1.0)
            + (amplitude - 1.0) * cos_omega
            + 2.0 * sqrt_amplitude * alpha
        )
        a1 = -2.0 * ((amplitude - 1.0) + (amplitude + 1.0) * cos_omega)
        a2 = (
            (amplitude + 1.0)
            + (amplitude - 1.0) * cos_omega
            - 2.0 * sqrt_amplitude * alpha
        )
    elif filter_type is BiquadType.HIGH_SHELF:
        b0 = amplitude * (
            (amplitude + 1.0)
            + (amplitude - 1.0) * cos_omega
            + 2.0 * sqrt_amplitude * alpha
        )
        b1 = -2.0 * amplitude * ((amplitude - 1.0) + (amplitude + 1.0) * cos_omega)
        b2 = amplitude * (
            (amplitude + 1.0)
            + (amplitude - 1.0) * cos_omega
            - 2.0 * sqrt_amplitude * alpha
        )
        a0 = (
            (amplitude + 1.0)
            - (amplitude - 1.0) * cos_omega
            + 2.0 * sqrt_amplitude * alpha
        )
        a1 = 2.0 * ((amplitude - 1.0) - (amplitude + 1.0) * cos_omega)
        a2 = (
            (amplitude + 1.0)
            - (amplitude - 1.0) * cos_omega
            - 2.0 * sqrt_amplitude * alpha
        )
    elif filter_type is BiquadType.LOW_PASS:
        b0 = (1.0 - cos_omega) / 2.0
        b1 = 1.0 - cos_omega
        b2 = (1.0 - cos_omega) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha
    elif filter_type is BiquadType.HIGH_PASS:
        b0 = (1.0 + cos_omega) / 2.0
        b1 = -(1.0 + cos_omega)
        b2 = (1.0 + cos_omega) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha
    elif filter_type is BiquadType.NOTCH:
        b0 = 1.0
        b1 = -2.0 * cos_omega
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha
    elif filter_type is BiquadType.BAND_PASS:
        # Constant 0 dB peak gain variant of the RBJ band-pass.
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha
    elif filter_type is BiquadType.ALL_PASS:
        b0 = 1.0 - alpha
        b1 = -2.0 * cos_omega
        b2 = 1.0 + alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha
    else:  # pragma: no cover - exhaustive Enum protection
        raise ValueError(f"unsupported filter type: {filter_type!r}")

    if a0 == 0.0:
        raise ValueError("degenerate filter: a0 is zero")
    coefficients = BiquadCoefficients(
        b0=b0 / a0,
        b1=b1 / a0,
        b2=b2 / a0,
        a1=a1 / a0,
        a2=a2 / a0,
    )
    for name in ("b0", "b1", "b2", "a1", "a2"):
        if not math.isfinite(getattr(coefficients, name)):
            raise ValueError("degenerate filter: non-finite coefficients")
    return coefficients
