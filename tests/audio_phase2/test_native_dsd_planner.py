"""AP2-F08 — Native DSD planner unit tests (§211, §213, §246)."""

from __future__ import annotations

import pytest

from michi.application.dsd_output_planner import (
    AlsaDsdTuple,
    NativeDsdOutputPlan,
    NativeDsdPlanner,
    NativeDsdPlannerError,
    NativeDsdQualification,
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)

DEVICE = "usb:152a:85dd"
LOCATOR = "hw:3,0"
EVIDENCE = "alsa-dsd:test"
U32_BE = AlsaDsdGrouping.DSD_U32_BE.alsa_format_name


def _source(
    *,
    bit_rate_hz: int = 2_822_400,
    packing: DsdPacking = DsdPacking.DSD_U8,
    bit_order: DsdBitOrder = DsdBitOrder.MSBF,
    organization: DsdOrganization = DsdOrganization.PLANAR,
    channels: int = 2,
) -> DsdSignalFormat:
    return DsdSignalFormat(
        bit_rate_hz=bit_rate_hz,
        channels=channels,
        packing=packing,
        bit_order=bit_order,
        organization=organization,
        layout=("FL", "FR") if channels == 2 else ("FC",),
    )


def _tuple(
    *,
    frame_rate_hz: int = 88_200,
    source_bits: int = 2_822_400,
    channels: int = 2,
    format_name: str = U32_BE,
) -> AlsaDsdTuple:
    width = (
        8
        if format_name == "SND_PCM_FORMAT_DSD_U8"
        else 16
        if "16" in format_name
        else 32
    )
    return AlsaDsdTuple(
        format_name=format_name,
        frame_rate_hz=frame_rate_hz,
        channels=channels,
        sample_width_bits=width,
        source_bits_per_second_per_channel=source_bits,
    )


def _qualification(
    requested: AlsaDsdTuple,
    *,
    supported: bool | None = True,
    generation: int = 1,
    device: str = DEVICE,
) -> NativeDsdQualification:
    return NativeDsdQualification(
        stable_device_id=device,
        binding_generation=generation,
        requested=requested,
        supported=supported,
        evidence_ref=EVIDENCE,
    )


def _plan(qualifications=None, source=None, execution_id="exec:1"):
    src = source or _source()
    quals = qualifications or (_qualification(_tuple()),)
    return NativeDsdPlanner().plan(
        stable_device_id=DEVICE,
        binding_locator=LOCATOR,
        binding_generation=1,
        source=src,
        qualifications=quals,
        execution_id=execution_id,
        source_proven=True,
        active_engine_id="gstreamer",
    )


def test_planner_returns_exact_native_plan() -> None:
    plan = _plan()
    assert isinstance(plan, NativeDsdOutputPlan)
    assert plan.gst_format == "DSDU32BE"
    assert plan.gst_rate_bytes_per_second_per_channel == 352_800
    assert plan.alsa_tuple.frame_rate_hz == 88_200
    assert plan.sink_factory == "alsasink"
    assert plan.normalize_reversed_bytes is False
    assert plan.represents_dsd_to_gst_conversion is True
    assert "DSD_SOURCE_PROVEN" in plan.decision_codes
    assert plan.plan_id.startswith("native-dsd:")


def test_planner_prefers_u32_but_remains_policy_explicit() -> None:
    source = _source()
    quals = (
        _qualification(
            _tuple(
                format_name="SND_PCM_FORMAT_DSD_U8",
                frame_rate_hz=352_800,
            )
        ),
        _qualification(_tuple()),
    )
    plan = _plan(quals, source)
    assert plan.gst_format == "DSDU32BE"


def test_lsbf_source_requires_bit_order_normalization() -> None:
    plan = _plan(source=_source(bit_order=DsdBitOrder.LSBF))
    assert plan.normalize_reversed_bytes is True
    assert "REVERSED_BYTES_NORMALIZATION" in plan.decision_codes


def test_native_interleaved_u32be_needs_no_representation_conversion() -> None:
    source = _source(
        packing=DsdPacking.DSD_U32BE,
        organization=DsdOrganization.INTERLEAVED,
    )
    plan = _plan(source=source)
    assert plan.represents_dsd_to_gst_conversion is False


def test_wrong_device_or_generation_is_not_a_candidate() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        _plan((_qualification(_tuple(), device="usb:other"),))
    assert info.value.code == "DSD_EXACT_TUPLE_UNKNOWN"

    with pytest.raises(NativeDsdPlannerError) as info:
        _plan((_qualification(_tuple(), generation=2),))
    assert info.value.code == "DSD_EXACT_TUPLE_UNKNOWN"


def test_negative_qualification_is_unsupported_not_unknown() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        _plan((_qualification(_tuple(), supported=False),))
    assert info.value.code == "DSD_EXACT_TUPLE_UNSUPPORTED"


def test_unknown_qualification_is_unknown_not_unsupported() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        _plan((_qualification(_tuple(), supported=None),))
    assert info.value.code == "DSD_EXACT_TUPLE_UNKNOWN"


def test_pcm_processing_active_is_refused() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        NativeDsdPlanner().plan(
            stable_device_id=DEVICE,
            binding_locator=LOCATOR,
            binding_generation=1,
            source=_source(),
            qualifications=(_qualification(_tuple()),),
            execution_id="exec:1",
            source_proven=True,
            active_engine_id="gstreamer",
            processing_active=True,
        )
    assert info.value.code == "DSD_PCM_PROCESSING_ACTIVE"


def test_non_gstreamer_engine_is_refused() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        NativeDsdPlanner().plan(
            stable_device_id=DEVICE,
            binding_locator=LOCATOR,
            binding_generation=1,
            source=_source(),
            qualifications=(_qualification(_tuple()),),
            execution_id="exec:1",
            source_proven=True,
            active_engine_id="mpd",
        )
    assert info.value.code == "DSD_ENGINE_UNSUPPORTED"


def test_unproven_source_is_refused() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        NativeDsdPlanner().plan(
            stable_device_id=DEVICE,
            binding_locator=LOCATOR,
            binding_generation=1,
            source=_source(),
            qualifications=(_qualification(_tuple()),),
            execution_id="exec:1",
            source_proven=False,
            active_engine_id="gstreamer",
        )
    assert info.value.code == "DSD_SOURCE_NOT_PROVEN"


def test_invalid_binding_and_execution_are_refused() -> None:
    for locator, generation, execution in (
        ("", 1, "exec:1"),
        (LOCATOR, -1, "exec:1"),
        (LOCATOR, 1, ""),
    ):
        with pytest.raises(NativeDsdPlannerError):
            NativeDsdPlanner().plan(
                stable_device_id=DEVICE,
                binding_locator=locator,
                binding_generation=generation,
                source=_source(),
                qualifications=(_qualification(_tuple()),),
                execution_id=execution,
                source_proven=True,
                active_engine_id="gstreamer",
            )


def test_plan_identity_is_deterministic_and_instance_bound() -> None:
    first = _plan(execution_id="exec:1")
    same = _plan(execution_id="exec:1")
    other = _plan(execution_id="exec:2")
    assert first.plan_id == same.plan_id
    assert first.plan_id != other.plan_id


def test_alsa_tuple_rejects_grouping_rate_mismatch() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        AlsaDsdTuple(
            format_name=U32_BE,
            frame_rate_hz=88_200,
            channels=2,
            sample_width_bits=32,
            source_bits_per_second_per_channel=2_822_400 + 1,
        )
    assert info.value.code == "DSD_ALSA_GROUPING_RATE_MISMATCH"


def test_alsa_tuple_rejects_format_width_disagreement() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        AlsaDsdTuple(
            format_name=U32_BE,
            frame_rate_hz=352_800,
            channels=2,
            sample_width_bits=8,
            source_bits_per_second_per_channel=2_822_400,
        )
    assert info.value.code == "DSD_ALSA_GROUPING_WIDTH_MISMATCH"


def test_qualification_rejects_a_non_tuple() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        NativeDsdQualification(
            stable_device_id=DEVICE,
            binding_generation=1,
            requested=object(),
            supported=True,
            evidence_ref=EVIDENCE,
        )
    assert info.value.code == "DSD_QUALIFICATION_TUPLE_INVALID"


def test_alsa_tuple_rejects_unknown_format() -> None:
    with pytest.raises(NativeDsdPlannerError) as info:
        AlsaDsdTuple(
            format_name="SND_PCM_FORMAT_S32_LE",
            frame_rate_hz=88_200,
            channels=2,
            sample_width_bits=32,
            source_bits_per_second_per_channel=2_822_400,
        )
    assert info.value.code == "DSD_ALSA_FORMAT_UNKNOWN"


@pytest.mark.parametrize(
    "bits,frame32,frame16,frame8",
    [
        (2_822_400, 88_200, 176_400, 352_800),
        (5_644_800, 176_400, 352_800, 705_600),
        (11_289_600, 352_800, 705_600, 1_411_200),
    ],
)
def test_dsd_rate_algebra(bits, frame32, frame16, frame8) -> None:
    for format_name, frame, width in (
        (U32_BE, frame32, 32),
        ("SND_PCM_FORMAT_DSD_U16_BE", frame16, 16),
        ("SND_PCM_FORMAT_DSD_U8", frame8, 8),
    ):
        tuple_ = AlsaDsdTuple(
            format_name=format_name,
            frame_rate_hz=frame,
            channels=2,
            sample_width_bits=width,
            source_bits_per_second_per_channel=bits,
        )
        assert tuple_.frame_rate_hz * width == bits
