"""AP2-F08 — ALSA DSD probe classification and opt-in hardware evidence."""

from __future__ import annotations

import errno
import os

import pytest

from michi.application.dsd_output_planner import AlsaDsdTuple
from michi.domain.dsd_signal import AlsaDsdGrouping
from michi.infrastructure.audio_devices.alsa_dsd_probe import (
    classify_alsa_dsd_result,
    probe_alsa_dsd,
)


def _tuple(frame: int = 88_200) -> AlsaDsdTuple:
    return AlsaDsdTuple(
        format_name=AlsaDsdGrouping.DSD_U32_BE.alsa_format_name,
        frame_rate_hz=frame,
        channels=2,
        sample_width_bits=32,
        source_bits_per_second_per_channel=frame * 32,
    )


def test_exact_negotiation_is_supported() -> None:
    requested = _tuple()
    assert classify_alsa_dsd_result(requested, requested, None) == (
        True,
        "ALSA_DSD_EXACT_NEGOTIATED",
    )


def test_readback_mismatch_is_negative() -> None:
    requested = _tuple()
    negotiated = _tuple(176_400)
    assert classify_alsa_dsd_result(requested, negotiated, None) == (
        False,
        "ALSA_DSD_READBACK_MISMATCH",
    )


def test_einval_is_the_only_exact_negative() -> None:
    assert classify_alsa_dsd_result(_tuple(), None, errno.EINVAL) == (
        False,
        "ALSA_DSD_EXACT_TUPLE_REJECTED",
    )


@pytest.mark.parametrize(
    "errno_code",
    [errno.EBUSY, errno.ENODEV, errno.EAGAIN, errno.EINTR, errno.ETIMEDOUT],
)
def test_transient_failures_are_unknown_never_unsupported(errno_code) -> None:
    assert classify_alsa_dsd_result(_tuple(), None, errno_code) == (
        None,
        "ALSA_DSD_PROBE_UNKNOWN",
    )


def test_missing_readback_is_unknown() -> None:
    assert classify_alsa_dsd_result(_tuple(), None, 0) == (
        None,
        "ALSA_DSD_READBACK_UNAVAILABLE",
    )


def test_unexpected_errno_is_unknown() -> None:
    assert classify_alsa_dsd_result(_tuple(), None, errno.EIO) == (
        None,
        "ALSA_DSD_PROBE_ERROR",
    )


def test_probe_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError):
        probe_alsa_dsd("", "hw:3,0", _tuple(), binding_generation=1)
    with pytest.raises(ValueError):
        probe_alsa_dsd("dev", "", _tuple(), binding_generation=1)
    with pytest.raises(ValueError):
        probe_alsa_dsd("dev", "hw:3,0", _tuple(), binding_generation=-1)
    with pytest.raises(TypeError):
        probe_alsa_dsd("dev", "hw:3,0", object(), binding_generation=1)


@pytest.mark.skipif(
    os.environ.get("MICHI_RUN_DSD_HARDWARE") != "1",
    reason="physical DSD ALSA probe requires the explicit operator gate",
)
def test_exact_dsd_hardware_probe_if_selected() -> None:
    locator = os.environ.get("MICHI_DSD_DEVICE", "hw:3,0")
    evidence = probe_alsa_dsd(
        "hardware:selected",
        locator,
        _tuple(),
        binding_generation=1,
    )
    assert evidence.supported is True, evidence.as_dict()
    assert evidence.negotiated is not None
