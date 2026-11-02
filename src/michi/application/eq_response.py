"""Calculated magnitude response for the F11 quick equalizer.

Pure, deterministic and independent of QML. It consumes the SAME RBJ
coefficient implementation as the graph compiler; it is a CALCULATED curve,
never a measurement of the audio signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from michi.domain.audio_processing import BiquadType
from michi.domain.biquad import biquad_coefficients, biquad_magnitude_db

_RESPONSE_POINTS = 256
_MIN_HZ = 20.0
_MAX_HZ = 20_000.0


@dataclass(frozen=True, slots=True)
class EqResponseCurve:
    points: tuple[tuple[float, float], ...]
    omitted_bands: int
    reason: str


def build_eq_response(
    *,
    rate_hz: float,
    bands: tuple[tuple[float, float, float], ...],
    preamp_db: float,
    points: int = _RESPONSE_POINTS,
) -> EqResponseCurve:
    """Build a log-spaced theoretical response from canonical coefficients.

    Bands at/above Nyquist are preserved in the draft by the caller, but they
    are not applied to this calculated curve. No sample-rate default is
    invented: the caller must provide the decoded signal rate.
    """
    if not math.isfinite(rate_hz) or rate_hz <= 0:
        raise ValueError("rate_hz must be finite and > 0")
    if not math.isfinite(preamp_db):
        raise ValueError("preamp_db must be finite")
    if points < 2:
        raise ValueError("points must be >= 2")
    nyquist = rate_hz / 2.0
    coefficients = []
    omitted = 0
    for frequency_hz, q, gain_db in bands:
        if (
            not math.isfinite(frequency_hz)
            or not math.isfinite(q)
            or not math.isfinite(gain_db)
        ):
            raise ValueError("bands must be finite")
        if frequency_hz <= 0 or q <= 0:
            raise ValueError("bands require positive frequency and Q")
        if frequency_hz >= nyquist:
            omitted += 1
            continue
        coefficients.append(
            biquad_coefficients(
                BiquadType.PEAK,
                rate_hz=rate_hz,
                frequency_hz=frequency_hz,
                q=q,
                gain_db=gain_db,
            )
        )
    top_hz = min(_MAX_HZ, 0.95 * nyquist)
    if top_hz <= _MIN_HZ:
        raise ValueError("Nyquist is too low for a response curve")
    log_low = math.log10(_MIN_HZ)
    log_span = math.log10(top_hz) - log_low
    curve: list[tuple[float, float]] = []
    for index in range(points):
        frequency = 10.0 ** (log_low + log_span * index / (points - 1))
        total = float(preamp_db)
        for item in coefficients:
            total += biquad_magnitude_db(item, rate_hz=rate_hz, frequency_hz=frequency)
        curve.append((frequency, total))
    reason = (
        f"{omitted} band(s) above Nyquist omitted"
        if omitted
        else "Calculated response from canonical coefficients"
    )
    return EqResponseCurve(tuple(curve), omitted, reason)


__all__ = ["EqResponseCurve", "build_eq_response"]
