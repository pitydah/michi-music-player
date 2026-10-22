"""AP2-F08 — Native DSD runtime branch inspector tests (§214.4)."""

from __future__ import annotations

import pytest

from michi.application.dsd_output_planner import (
    AlsaDsdTuple,
    NativeDsdPlanner,
    NativeDsdQualification,
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from michi.infrastructure.audio_output.dsd_runtime_inspector import (
    NativeDsdBranchError,
    ObservedCaps,
    inspect_native_dsd_branch,
)
from michi.infrastructure.audio_output.strict_dsd_sink import recipe_from_native_plan

DEVICE = "usb:152a:85dd"
LOCATOR = "hw:3,0"


def _recipe():
    source = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    requested = AlsaDsdTuple(
        format_name=AlsaDsdGrouping.DSD_U32_BE.alsa_format_name,
        frame_rate_hz=88_200,
        channels=2,
        sample_width_bits=32,
        source_bits_per_second_per_channel=2_822_400,
    )
    plan = NativeDsdPlanner().plan(
        stable_device_id=DEVICE,
        binding_locator=LOCATOR,
        binding_generation=1,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id=DEVICE,
                binding_generation=1,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:test",
            ),
        ),
        execution_id="exec:inspect",
        source_proven=True,
        active_engine_id="gstreamer",
    )
    return recipe_from_native_plan(plan)


def _caps(media_type: str, **fields: str) -> ObservedCaps:
    return ObservedCaps(
        media_type, tuple((key, str(value)) for key, value in fields.items())
    )


def _source_caps() -> ObservedCaps:
    return _caps(
        "audio/x-dsd",
        format="DSDU8",
        rate="352800",
        channels="2",
        layout="non-interleaved",
        **{"reversed-bytes": "false"},
    )


def _sink_caps(**overrides: str) -> ObservedCaps:
    fields = {
        "format": "DSDU32BE",
        "rate": "352800",
        "channels": "2",
        "layout": "interleaved",
        "reversed-bytes": "false",
    }
    fields.update(overrides)
    return _caps("audio/x-dsd", **fields)


def test_clean_dsd_branch_is_proven() -> None:
    evidence = inspect_native_dsd_branch(
        (_source_caps(), _sink_caps()),
        _recipe(),
        factories=("avdemux_dsf", "dsdconvert", "alsasink"),
    )
    assert evidence.contains_audio_x_raw is False
    assert evidence.sink_format == "DSDU32BE"
    assert evidence.sink_rate_bytes_per_second_per_channel == 352_800
    assert evidence.sink_channels == 2
    assert evidence.sink_layout == "interleaved"
    assert evidence.sink_reversed_bytes is False


def test_any_raw_cap_is_a_conversion_contradiction() -> None:
    raw = _caps("audio/x-raw", format="F32LE", rate="352800", channels="2")
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch((_source_caps(), raw, _sink_caps()), _recipe())
    assert info.value.code == "NATIVE_DSD_PCM_CONVERSION_DETECTED"


def test_unplanned_decoder_factory_is_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch(
            (_sink_caps(),),
            _recipe(),
            factories=("avdec_dsd_msbf_planar", "alsasink"),
        )
    assert info.value.code == "NATIVE_DSD_UNPLANNED_DECODER"


def test_missing_dsd_caps_is_not_proven() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch((), _recipe())
    assert info.value.code == "NATIVE_DSD_BRANCH_NOT_PROVEN"


def test_incomplete_branch_is_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch(
            (_sink_caps(),), _recipe(), graph_inspection_complete=False
        )
    assert info.value.code == "NATIVE_DSD_BRANCH_NOT_INSPECTABLE"


def test_missing_caps_field_is_typed() -> None:
    incomplete = _caps("audio/x-dsd", format="DSDU32BE", rate="352800", channels="2")
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch((incomplete,), _recipe())
    assert info.value.code == "NATIVE_DSD_CAPS_INCOMPLETE"


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"format": "DSDU16BE"}, "NATIVE_DSD_FORMAT_MISMATCH"),
        ({"rate": "176400"}, "NATIVE_DSD_RATE_MISMATCH"),
        ({"channels": "1"}, "NATIVE_DSD_CHANNELS_MISMATCH"),
        ({"layout": "non-interleaved"}, "NATIVE_DSD_LAYOUT_UNSUPPORTED"),
        ({"reversed-bytes": "true"}, "NATIVE_DSD_REVERSED_BYTES_AT_SINK"),
    ],
)
def test_sink_caps_mismatch_is_refused(overrides, code) -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch((_sink_caps(**overrides),), _recipe())
    assert info.value.code == code


def test_invalid_numeric_caps_is_typed() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        inspect_native_dsd_branch((_sink_caps(rate="not-a-rate"),), _recipe())
    assert info.value.code == "NATIVE_DSD_CAPS_INVALID"
