"""F11 calculated EQ response: canonical coefficients, never a measurement."""

from __future__ import annotations

import pytest

from michi.application.eq_response import build_eq_response

_RATE = 48_000.0
_CENTERS = (
    31.25,
    62.5,
    125.0,
    250.0,
    500.0,
    1_000.0,
    2_000.0,
    4_000.0,
    8_000.0,
    16_000.0,
)


def _bands(gains: tuple[float, ...]) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        (center, 2.0**0.5, gain) for center, gain in zip(_CENTERS, gains, strict=True)
    )


def test_flat_curve_is_zero_db_with_log_spacing() -> None:
    curve = build_eq_response(
        rate_hz=_RATE,
        bands=_bands((0.0,) * 10),
        preamp_db=0.0,
    )
    assert len(curve.points) == 256
    assert curve.omitted_bands == 0
    assert curve.points[0][0] == pytest.approx(20.0)
    assert curve.points[-1][0] == pytest.approx(20_000.0)
    assert all(abs(db) < 1e-9 for _hz, db in curve.points)


def test_peak_center_is_the_designed_gain_and_preamp_is_linear() -> None:
    bands = list(_bands((0.0,) * 10))
    bands[5] = (1_000.0, 2.0**0.5, 6.0)
    curve = build_eq_response(
        rate_hz=_RATE,
        bands=tuple(bands),
        preamp_db=-2.0,
    )
    point = min(curve.points, key=lambda item: abs(item[0] - 1_000.0))
    assert point[1] == pytest.approx(4.0, abs=0.01)


def test_bands_above_nyquist_are_omitted_not_faked() -> None:
    curve = build_eq_response(
        rate_hz=16_000.0,
        bands=_bands((0.0,) * 10),
        preamp_db=0.0,
    )
    # 8 kHz and 16 kHz are at/above Nyquist; the rest remain valid.
    assert curve.omitted_bands == 2
    assert "Nyquist" in curve.reason
    assert curve.points[-1][0] < 16_000.0 * 0.5


def test_invalid_signal_rate_fails_closed() -> None:
    with pytest.raises(ValueError):
        build_eq_response(rate_hz=0.0, bands=_bands((0.0,) * 10), preamp_db=0.0)
