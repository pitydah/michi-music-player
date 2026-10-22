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


class _FakeAlsa:
    """Deterministic ALSA call log for sequencing/cleanup tests."""

    def __init__(self, fail_at: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail_at = fail_at

    def _rc(self, name: str) -> int:
        self.calls.append(name)
        return -errno.EBUSY if self.fail_at == name else 0

    def snd_pcm_open(self, handle_ref, name, stream, mode):
        rc = self._rc("open")
        if rc == 0:
            handle_ref._obj.value = 1
        return rc

    def snd_pcm_hw_params_malloc(self, params_ref):
        rc = self._rc("malloc")
        if rc == 0:
            params_ref._obj.value = 2
        return rc

    def snd_pcm_hw_params_any(self, pcm, params):
        return self._rc("any")

    def snd_pcm_hw_params_set_rate_resample(self, pcm, params, enabled):
        return self._rc("rate_resample")

    def snd_pcm_hw_params_set_access(self, pcm, params, access):
        return self._rc("access")

    def snd_pcm_hw_params_set_channels(self, pcm, params, channels):
        return self._rc("channels")

    def snd_pcm_hw_params_set_format(self, pcm, params, format_id):
        return self._rc("format")

    def snd_pcm_hw_params_set_rate(self, pcm, params, rate, direction):
        return self._rc("rate")

    def snd_pcm_hw_params(self, pcm, params):
        return self._rc("hw_params")

    def snd_pcm_hw_params_get_format(self, params, fmt_ref):
        rc = self._rc("get_format")
        if rc == 0:
            fmt_ref._obj.value = 52
        return rc

    def snd_pcm_hw_params_get_rate(self, params, rate_ref, dir_ref):
        rc = self._rc("get_rate")
        if rc == 0:
            rate_ref._obj.value = 88_200
        return rc

    def snd_pcm_hw_params_get_channels(self, params, channels_ref):
        rc = self._rc("get_channels")
        if rc == 0:
            channels_ref._obj.value = 2
        return rc

    def snd_pcm_close(self, pcm):
        self.calls.append("close")
        return 0

    def snd_pcm_hw_params_free(self, params):
        self.calls.append("free")

    def snd_strerror(self, rc):
        return b"fake-alsa-error"


def _probe_with(fake: _FakeAlsa):
    return probe_alsa_dsd(
        "usb:test",
        "hw:3,0",
        _tuple(),
        binding_generation=1,
        environment="test",
        library=fake,
    )


def test_fake_library_success_reaches_readback() -> None:
    fake = _FakeAlsa()
    evidence = _probe_with(fake)
    assert evidence.supported is True
    assert evidence.negotiated == _tuple()
    assert fake.calls[-2:] == ["free", "close"] or fake.calls[-2:] == ["close", "free"]


def test_fake_library_open_failure_does_not_allocate_or_close() -> None:
    fake = _FakeAlsa("open")
    evidence = _probe_with(fake)
    assert evidence.supported is None
    assert "malloc" not in fake.calls
    assert "close" not in fake.calls
    assert "free" not in fake.calls


@pytest.mark.parametrize(
    "fail_at,forbidden",
    [
        ("malloc", "any"),
        ("any", "rate_resample"),
        ("rate_resample", "access"),
        ("access", "channels"),
        ("channels", "format"),
        ("format", "rate"),
        ("rate", "hw_params"),
        ("hw_params", "get_format"),
        ("get_format", "get_rate"),
        ("get_rate", "get_channels"),
    ],
)
def test_fake_library_stops_at_first_failure(fail_at, forbidden) -> None:
    fake = _FakeAlsa(fail_at)
    evidence = _probe_with(fake)
    assert evidence.supported is None
    assert fail_at in fake.calls
    assert forbidden not in fake.calls
    if fail_at != "malloc":
        assert "free" in fake.calls
    assert "close" in fake.calls


def test_fake_library_get_channels_failure_is_unknown() -> None:
    fake = _FakeAlsa("get_channels")
    evidence = _probe_with(fake)
    assert evidence.supported is None
    assert evidence.disposition == "ALSA_DSD_READBACK_UNAVAILABLE"
    assert "close" in fake.calls and "free" in fake.calls
