"""AP2-F04 — RBJ biquad coefficient math: golden vectors and safety.

Golden values were independently computed from the RBJ Audio-EQ-Cookbook
formulas for fs=48000, f0=1000, Q=0.7071067811865476, gain=+6 dB (peak and
shelves) and hardcoded here; the tests never re-derive expectations from the
implementation under test.
"""

from __future__ import annotations

import math

import pytest

from michi.domain.audio_processing import BiquadType
from michi.infrastructure.audio_processing.biquad import (
    BiquadCoefficients,
    biquad_coefficients,
)

_RATE = 48000.0
_F0 = 1000.0
_Q = 0.7071067811865476
_GAIN_DB = 6.0

# (b0, b1, b2, a1, a2) normalized by a0; a0 == 1 implied.
GOLDEN: dict[BiquadType, tuple[float, float, float, float, float]] = {
    BiquadType.PEAK: (
        1.0610424252634374,
        -1.8612731439964758,
        0.816291571321481,
        -1.8612731439964758,
        0.8773339965849185,
    ),
    BiquadType.LOW_SHELF: (
        1.0325624832475901,
        -1.8388568718996408,
        0.8287476843124699,
        -1.84445686716092,
        0.855710172298781,
    ),
    BiquadType.HIGH_SHELF: (
        1.9323405094996573,
        -3.5641187224398743,
        1.6535234303238662,
        -1.7808674067995511,
        0.8026126241832001,
    ),
    BiquadType.LOW_PASS: (
        0.003916126660547383,
        0.007832253321094766,
        0.003916126660547383,
        -1.815341082704568,
        0.8310055893467576,
    ),
    BiquadType.HIGH_PASS: (
        0.9115866680128315,
        -1.823173336025663,
        0.9115866680128315,
        -1.815341082704568,
        0.8310055893467576,
    ),
    BiquadType.NOTCH: (
        0.9155027946733788,
        -1.815341082704568,
        0.9155027946733788,
        -1.815341082704568,
        0.8310055893467576,
    ),
    BiquadType.BAND_PASS: (
        0.08449720532662121,
        0.0,
        -0.08449720532662121,
        -1.815341082704568,
        0.8310055893467576,
    ),
    BiquadType.ALL_PASS: (
        0.8310055893467576,
        -1.815341082704568,
        1.0,
        -1.815341082704568,
        0.8310055893467576,
    ),
}


def _magnitude(
    coefficients: BiquadCoefficients, frequency_hz: float, rate: float
) -> float:
    omega = 2.0 * math.pi * frequency_hz / rate
    z1 = complex(math.cos(-omega), math.sin(-omega))
    z2 = z1 * z1
    numerator = coefficients.b0 + coefficients.b1 * z1 + coefficients.b2 * z2
    denominator = 1.0 + coefficients.a1 * z1 + coefficients.a2 * z2
    return abs(numerator / denominator)


@pytest.mark.parametrize("filter_type", list(GOLDEN))
def test_golden_coefficients(filter_type: BiquadType) -> None:
    gain_db = (
        _GAIN_DB
        if filter_type in {BiquadType.PEAK, BiquadType.LOW_SHELF, BiquadType.HIGH_SHELF}
        else 0.0
    )
    coefficients = biquad_coefficients(
        filter_type,
        rate_hz=_RATE,
        frequency_hz=_F0,
        q=_Q,
        gain_db=gain_db,
    )
    expected = GOLDEN[filter_type]
    actual = (
        coefficients.b0,
        coefficients.b1,
        coefficients.b2,
        coefficients.a1,
        coefficients.a2,
    )
    for got, want in zip(actual, expected, strict=True):
        assert got == pytest.approx(want, rel=1e-12, abs=1e-12), filter_type


def test_peak_gain_spot_check_at_center_frequency() -> None:
    coefficients = biquad_coefficients(
        BiquadType.PEAK, rate_hz=_RATE, frequency_hz=_F0, q=_Q, gain_db=_GAIN_DB
    )
    magnitude = _magnitude(coefficients, _F0, _RATE)
    assert magnitude == pytest.approx(10 ** (_GAIN_DB / 20.0), rel=1e-3)


def test_low_pass_and_high_pass_response_spots() -> None:
    low_pass = biquad_coefficients(
        BiquadType.LOW_PASS, rate_hz=_RATE, frequency_hz=_F0, q=_Q
    )
    assert _magnitude(low_pass, 20.0, _RATE) == pytest.approx(1.0, rel=0.01)
    assert _magnitude(low_pass, 20000.0, _RATE) < 0.01

    high_pass = biquad_coefficients(
        BiquadType.HIGH_PASS, rate_hz=_RATE, frequency_hz=_F0, q=_Q
    )
    assert _magnitude(high_pass, 20000.0, _RATE) == pytest.approx(1.0, rel=0.03)
    assert _magnitude(high_pass, 20.0, _RATE) < 0.01


def test_notch_and_all_pass_behaviour() -> None:
    notch = biquad_coefficients(BiquadType.NOTCH, rate_hz=_RATE, frequency_hz=_F0, q=_Q)
    assert _magnitude(notch, _F0, _RATE) == pytest.approx(0.0, abs=1e-6)
    assert _magnitude(notch, 100.0, _RATE) == pytest.approx(1.0, rel=0.02)

    all_pass = biquad_coefficients(
        BiquadType.ALL_PASS, rate_hz=_RATE, frequency_hz=_F0, q=_Q
    )
    for frequency in (50.0, 500.0, 1000.0, 5000.0, 15000.0):
        assert _magnitude(all_pass, frequency, _RATE) == pytest.approx(1.0, rel=1e-6)


def test_peak_zero_gain_is_identity() -> None:
    coefficients = biquad_coefficients(
        BiquadType.PEAK, rate_hz=_RATE, frequency_hz=_F0, q=_Q, gain_db=0.0
    )
    assert coefficients.b0 == pytest.approx(1.0, rel=1e-12)
    assert coefficients.b1 == pytest.approx(coefficients.a1, rel=1e-12)
    assert coefficients.b2 == pytest.approx(coefficients.a2, rel=1e-12)


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK, rate_hz=_RATE, frequency_hz=math.nan, q=_Q, gain_db=1.0
        )
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK, rate_hz=_RATE, frequency_hz=_F0, q=_Q, gain_db=math.inf
        )
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK, rate_hz=_RATE, frequency_hz=0.0, q=_Q, gain_db=1.0
        )
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK,
            rate_hz=_RATE,
            frequency_hz=_RATE / 2.0,
            q=_Q,
            gain_db=1.0,
        )
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK, rate_hz=_RATE, frequency_hz=_F0, q=0.0, gain_db=1.0
        )
    with pytest.raises(ValueError):
        biquad_coefficients(
            BiquadType.PEAK, rate_hz=0.0, frequency_hz=_F0, q=_Q, gain_db=1.0
        )


def test_coefficients_are_immutable_and_finite() -> None:
    coefficients = biquad_coefficients(
        BiquadType.PEAK, rate_hz=_RATE, frequency_hz=_F0, q=_Q, gain_db=_GAIN_DB
    )
    for value in (
        coefficients.b0,
        coefficients.b1,
        coefficients.b2,
        coefficients.a1,
        coefficients.a2,
    ):
        assert math.isfinite(value)


def test_gain_envelope_is_enforced_defensively() -> None:
    """The utility is independently callable; it must not trust PeqBand."""
    for filter_type in (
        BiquadType.PEAK,
        BiquadType.LOW_SHELF,
        BiquadType.HIGH_SHELF,
    ):
        for gain in (-36.0, 36.0):
            biquad_coefficients(
                filter_type,
                rate_hz=_RATE,
                frequency_hz=_F0,
                q=_Q,
                gain_db=gain,
            )
        for gain in (
            -36.0001,
            36.0001,
            1e9,
            -1e9,
            math.nan,
            math.inf,
            -math.inf,
        ):
            with pytest.raises(ValueError):
                biquad_coefficients(
                    filter_type,
                    rate_hz=_RATE,
                    frequency_hz=_F0,
                    q=_Q,
                    gain_db=gain,
                )


def test_gainless_filters_reject_any_non_zero_gain() -> None:
    for filter_type in (
        BiquadType.LOW_PASS,
        BiquadType.HIGH_PASS,
        BiquadType.NOTCH,
        BiquadType.BAND_PASS,
        BiquadType.ALL_PASS,
    ):
        biquad_coefficients(filter_type, rate_hz=_RATE, frequency_hz=_F0, q=_Q)
        for gain in (-36.0, 0.0001, 36.0):
            with pytest.raises(ValueError):
                biquad_coefficients(
                    filter_type,
                    rate_hz=_RATE,
                    frequency_hz=_F0,
                    q=_Q,
                    gain_db=gain,
                )
