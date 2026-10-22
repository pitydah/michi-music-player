"""AP2-F08 — strict host payload validation (no Gst required)."""

from __future__ import annotations

import pytest

from michi.infrastructure.audio_engines.gstreamer_host_native_dsd import (
    NativeDsdHostError,
    _parse_request,
)


def _payload(**overrides):
    payload = {
        "path": "/tmp/source.dsf",
        "plan_id": "native-dsd:plan",
        "execution_id": "exec:1",
        "binding_generation": 1,
        "stable_device_id": "usb:152a:85dd",
        "locator": "hw:3,0",
        "gst_format": "DSDU32BE",
        "gst_rate_bytes_per_second_per_channel": 352_800,
        "channels": 2,
        "source_bits_per_second_per_channel": 2_822_400,
        "normalize_reversed_bytes": False,
        "requires_dsdconvert": True,
        "source_family": "dsf",
        "sink_factory": "alsasink",
    }
    payload.update(overrides)
    return payload


def test_valid_payload_parses_with_zero_generation() -> None:
    request = _parse_request(_payload(binding_generation=0))
    assert request.plan_id == "native-dsd:plan"
    assert request.binding_generation == 0
    assert request.sink_factory == "alsasink"


@pytest.mark.parametrize(
    "overrides",
    [
        {"path": ""},
        {"plan_id": 1},
        {"execution_id": None},
        {"binding_generation": -1},
        {"binding_generation": True},
        {"gst_rate_bytes_per_second_per_channel": 0},
        {"channels": True},
        ({"gst_format": "S32LE"}, "NATIVE_DSD_HOST_FORMAT_INVALID"),
        ({"source_family": "wav"}, "NATIVE_DSD_HOST_FAMILY_INVALID"),
        ({"sink_factory": "pulsesink"}, "NATIVE_DSD_HOST_SINK_INVALID"),
        {"normalize_reversed_bytes": 0},
        {"requires_dsdconvert": "yes"},
    ],
)
def test_invalid_payload_fields_are_typed(overrides) -> None:
    if isinstance(overrides, tuple):
        overrides, expected = overrides
    else:
        expected = "NATIVE_DSD_HOST_PAYLOAD_INVALID"
    with pytest.raises(NativeDsdHostError) as info:
        _parse_request(_payload(**overrides))
    assert info.value.code == expected


def test_fakesink_requires_the_explicit_lab_switch(monkeypatch) -> None:
    monkeypatch.delenv("MICHI_GST_LAB_SINK", raising=False)
    with pytest.raises(NativeDsdHostError) as info:
        _parse_request(_payload(sink_factory="fakesink"))
    assert info.value.code == "NATIVE_DSD_HOST_SINK_FORBIDDEN"

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    assert _parse_request(_payload(sink_factory="fakesink")).sink_factory == "fakesink"
