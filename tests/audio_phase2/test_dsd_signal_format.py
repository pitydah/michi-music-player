"""DsdSignalFormat derived DoP carrier facts."""

from __future__ import annotations

import pytest

from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)


def _format(bit_rate_hz: int) -> DsdSignalFormat:
    return DsdSignalFormat(
        bit_rate_hz=bit_rate_hz,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.LSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )


def test_format_derives_the_dop_carrier_rate_from_the_source_rate() -> None:
    assert _format(2_822_400).dop_carrier_frames_per_second == 176_400


def test_format_rejects_a_dop_carrier_rate_that_is_not_divisible_by_16() -> None:
    with pytest.raises(ValueError, match="divisible by 16"):
        _ = _format(2_822_408).dop_carrier_frames_per_second
