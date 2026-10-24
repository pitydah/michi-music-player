"""AP2-F09 — exact ALSA DoP carrier qualification."""

from __future__ import annotations

import errno
import os

import pytest

from michi.domain.dop import DopCarrierLayout, DopCarrierSupport
from michi.infrastructure.audio_devices.alsa_dop_probe import (
    AlsaDopProbeError,
    DopCarrierProbeRequest,
    classify_dop_probe_result,
    probe_dop_carrier,
)


def _request(
    layout=DopCarrierLayout.PACKED_24_LE, rate=176_400
) -> DopCarrierProbeRequest:
    from michi.domain.dop import memory_contract_for

    contract = memory_contract_for(layout)
    return DopCarrierProbeRequest(layout, contract.alsa_format, rate)


def test_exact_readback_is_qualified() -> None:
    request = _request()
    assert classify_dop_probe_result(
        request, request.rate_hz, request.alsa_format, 2, None
    ) == (DopCarrierSupport.QUALIFIED, "DOP_CARRIER_EXACT_NEGOTIATED")


def test_readback_mismatch_is_negative() -> None:
    request = _request()
    assert classify_dop_probe_result(
        request, 352_800, request.alsa_format, 2, None
    ) == (DopCarrierSupport.UNSUPPORTED, "DOP_CARRIER_READBACK_MISMATCH")


def test_einval_is_exact_negative_and_busy_is_unknown() -> None:
    request = _request()
    assert classify_dop_probe_result(request, None, None, None, errno.EINVAL) == (
        DopCarrierSupport.UNSUPPORTED,
        "DOP_CARRIER_EXACT_TUPLE_REJECTED",
    )
    assert classify_dop_probe_result(request, None, None, None, errno.EBUSY) == (
        DopCarrierSupport.UNKNOWN,
        "DOP_CARRIER_PROBE_UNKNOWN",
    )


def test_format_must_match_layout_contract() -> None:
    with pytest.raises(AlsaDopProbeError):
        DopCarrierProbeRequest(DopCarrierLayout.PACKED_24_LE, "S32_LE", 176_400, 2)


@pytest.mark.skipif(
    os.environ.get("MICHI_RUN_DOP_HARDWARE") != "1",
    reason="physical DoP carrier qualification requires the operator gate",
)
def test_exact_dop_carrier_on_selected_dac() -> None:
    device = os.environ.get("MICHI_DSD_DEVICE", "hw:3,0")
    packed = probe_dop_carrier(
        "usb:152a:85dd",
        device,
        1,
        _request(DopCarrierLayout.PACKED_24_LE),
        environment="hardware:lab",
    )
    # This observed SMSL endpoint exposes S32_LE, not S24_3LE. The probe must
    # report that exact negative, not infer support from PCM rate alone.
    assert packed.support is DopCarrierSupport.UNSUPPORTED, packed.as_dict()
    lsb = probe_dop_carrier(
        "usb:152a:85dd",
        device,
        1,
        _request(DopCarrierLayout.S32_LE_LSB24),
        environment="hardware:lab",
    )
    assert lsb.support is DopCarrierSupport.QUALIFIED, lsb.as_dict()
    assert lsb.negotiated_rate_hz == 176_400
