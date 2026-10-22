"""AP2-F08 — Native DSD branch inspector with real pad identity."""

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
    NEGOTIATED_CURRENT,
    TEMPLATE_CAPABILITY,
    NativeDsdBranchError,
    ObservedPad,
    inspect_native_dsd_branch,
)
from michi.infrastructure.audio_output.strict_dsd_sink import recipe_from_native_plan

DEVICE = "hw:3,0"
EXEC = "exec:inspect"


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
        stable_device_id="usb:152a:85dd",
        binding_locator=DEVICE,
        binding_generation=1,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id="usb:152a:85dd",
                binding_generation=1,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:test",
            ),
        ),
        execution_id=EXEC,
        source_proven=True,
        active_engine_id="gstreamer",
    )
    return recipe_from_native_plan(plan)


def _fields(**values: str) -> tuple[tuple[str, str], ...]:
    return tuple((key, str(value)) for key, value in values.items())


def _source_pad(**overrides) -> ObservedPad:
    data = dict(
        element_name="demux",
        factory="avdemux_dsf",
        pad_name="audio_0",
        direction="src",
        role="source",
        media_type="audio/x-dsd",
        fields=_fields(
            format="DSDU8",
            rate="352800",
            channels="2",
            layout="non-interleaved",
            **{"reversed-bytes": "false"},
        ),
        caps_state=NEGOTIATED_CURRENT,
        linked=True,
        selected_device=DEVICE,
        execution_id=EXEC,
        binding_generation=1,
    )
    data.update(overrides)
    return ObservedPad(**data)


def _sink_pad(**overrides) -> ObservedPad:
    data = dict(
        element_name="alsa",
        factory="alsasink",
        pad_name="sink",
        direction="sink",
        role="sink",
        media_type="audio/x-dsd",
        fields=_fields(
            format="DSDU32BE",
            rate="352800",
            channels="2",
            layout="interleaved",
            **{"reversed-bytes": "false"},
        ),
        caps_state=NEGOTIATED_CURRENT,
        linked=True,
        selected_device=DEVICE,
        execution_id=EXEC,
        binding_generation=1,
    )
    data.update(overrides)
    return ObservedPad(**data)


def _inspect(observations, **kwargs):
    return inspect_native_dsd_branch(
        observations,
        _recipe(),
        expected_execution_id=EXEC,
        expected_binding_generation=1,
        expected_device=DEVICE,
        **kwargs,
    )


def test_clean_identity_based_branch_is_proven() -> None:
    evidence = _inspect((_source_pad(), _sink_pad()))
    assert evidence.contains_audio_x_raw is False
    assert evidence.sink_pad.pad_name == "sink"
    assert evidence.sink_format == "DSDU32BE"
    assert evidence.sink_rate_bytes_per_second_per_channel == 352_800


def test_reordered_observations_are_identity_based_not_ordinal() -> None:
    evidence = _inspect((_sink_pad(), _source_pad()))
    assert evidence.sink_pad.element_name == "alsa"


def test_raw_negotiated_cap_is_a_conversion_contradiction() -> None:
    raw = _source_pad(
        element_name="decoder",
        factory="avdec_dsd_msbf_planar",
        media_type="audio/x-raw",
        role="other",
    )
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), raw, _sink_pad()))
    assert info.value.code == "NATIVE_DSD_UNPLANNED_DECODER"

    raw_ok_factory = _source_pad(
        element_name="converter",
        factory="audioconvert",
        media_type="audio/x-raw",
        role="other",
    )
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), raw_ok_factory, _sink_pad()))
    assert info.value.code == "NATIVE_DSD_PCM_CONVERSION_DETECTED"


def test_dsd_caps_on_a_non_selected_element_do_not_prove_a_sink() -> None:
    fake = _sink_pad(factory="fakesink", element_name="fake")
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), fake))
    assert info.value.code == "NATIVE_DSD_SINK_IDENTITY_MISSING"


def test_template_only_sink_caps_are_not_evidence() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad(caps_state=TEMPLATE_CAPABILITY)))
    assert info.value.code == "NATIVE_DSD_SINK_CAPS_NOT_NEGOTIATED"


def test_unlinked_sink_pad_is_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad(linked=False)))
    assert info.value.code == "NATIVE_DSD_SINK_PAD_UNLINKED"


def test_sink_device_mismatch_is_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad(selected_device="hw:9,0")))
    assert info.value.code == "NATIVE_DSD_SINK_DEVICE_MISMATCH"


def test_other_device_dsd_caps_do_not_suffice() -> None:
    other = _source_pad(selected_device="hw:9,0")
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((other, _sink_pad()))
    assert info.value.code == "NATIVE_DSD_STALE_DEVICE"


def test_stale_execution_and_generation_are_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad(execution_id="exec:old")))
    assert info.value.code == "NATIVE_DSD_STALE_EXECUTION"

    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad(binding_generation=2)))
    assert info.value.code == "NATIVE_DSD_STALE_EXECUTION"


def test_missing_sink_or_source_is_not_proven() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(),))
    assert info.value.code == "NATIVE_DSD_SINK_IDENTITY_MISSING"

    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_sink_pad(),))
    assert info.value.code == "NATIVE_DSD_BRANCH_NOT_PROVEN"


def test_incomplete_graph_is_refused() -> None:
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), _sink_pad()), graph_inspection_complete=False)
    assert info.value.code == "NATIVE_DSD_BRANCH_NOT_INSPECTABLE"


def test_missing_sink_field_is_typed() -> None:
    incomplete = _sink_pad(
        fields=_fields(format="DSDU32BE", rate="352800", channels="2")
    )
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), incomplete))
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
    sink = _sink_pad(
        fields=_fields(
            **{
                "format": "DSDU32BE",
                "rate": "352800",
                "channels": "2",
                "layout": "interleaved",
                "reversed-bytes": "false",
                **overrides,
            }
        )
    )
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), sink))
    assert info.value.code == code


def test_invalid_numeric_sink_caps_is_typed() -> None:
    sink = _sink_pad(
        fields=_fields(
            format="DSDU32BE",
            rate="not-a-rate",
            channels="2",
            layout="interleaved",
            **{"reversed-bytes": "false"},
        )
    )
    with pytest.raises(NativeDsdBranchError) as info:
        _inspect((_source_pad(), sink))
    assert info.value.code == "NATIVE_DSD_CAPS_INVALID"
