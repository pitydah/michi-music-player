"""DAC-V35-040 — OutputPlanner gates (§17/§18/§19/§403).

Puro/determinista, sin I/O: READY con carrier exacto, rechazos
explícitos, nunca fallback silencioso de rate ni remix.
"""

from __future__ import annotations

import pytest

from michi.application.audio_output_planner import (
    BINDING_ALSA_HW_SELECTED,
    BINDING_GENERATION_CHANGED,
    ENGINE_GSTREAMER_DIRECT,
    ENGINE_NOT_GSTREAMER,
    EXACT_TUPLE_UNKNOWN,
    EXACT_TUPLE_UNSUPPORTED,
    FALLBACK_STOP,
    FIXED_VOLUME_SELECTED,
    NO_ALSA_HW_BINDING,
    PATH_NOT_HARDWARE_DIRECT,
    S32_CARRIER_PRESERVES_24_BITS,
    SELECTED_DEVICE_MISSING,
    SOURCE_RATE_UNKNOWN,
    STRICT_NO_REMIX,
    STRICT_NO_RESAMPLE,
    OutputPlanner,
    PlannerFacts,
    PlannerRefusal,
    carrier_tuple,
)
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    DecodedSourceSignal,
    EvidenceStrength,
    PcmTuple,
)
from michi.domain.audio_output import (
    OutputPathPreference,
    OutputPlan,
    PathSemantics,
    sink_spec_for,
    stable_direct_preset,
)

DEVICE = "usb:2622:0105:DX5ABC123"


def _source(rate: int = 96000, bits: int | None = 24, channels: int = 2):
    return DecodedSourceSignal(
        encoding="pcm",
        rate_hz=rate,
        significant_bits=bits,
        channels=channels,
        channel_positions=("FL", "FR"),
    )


def _binding(generation: int = 1, available: bool = True):
    return AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=DX5,DEV=0",
        generation=generation,
        currently_available=available,
        card_index=1,
        pcm_device=0,
    )


def _evidence(
    rate: int = 96000,
    fmt: str = "S32_LE",
    channels: int = 2,
    bits: int = 24,
    supported: bool | None = True,
    refs: tuple[str, ...] = ("probe:1",),
):
    return CapabilityEvidence(
        stable_device_id=DEVICE,
        tuple=PcmTuple(rate, fmt, channels, bits),
        supported=supported,
        strength=EvidenceStrength.OPENED if supported else EvidenceStrength.PROBED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint="fp",
        evidence_refs=refs,
    )


def _facts(**overrides) -> PlannerFacts:
    base = dict(
        active_engine_id="gstreamer",
        profile=stable_direct_preset("p1", DEVICE),
        selected_device_id=DEVICE,
        binding=_binding(),
        source=_source(),
        evidence=(_evidence(),),
    )
    base.update(overrides)
    return PlannerFacts(**base)


def test_ready_plan_24_96_with_s32_carrier() -> None:
    plan = OutputPlanner().plan(_facts())
    assert isinstance(plan, OutputPlan)
    assert plan.path_semantics is PathSemantics.HARDWARE_RAW
    assert plan.stable_device_id == DEVICE
    assert plan.requested_pcm == PcmTuple(96000, "S32_LE", 2, 24)
    assert plan.binding.locator == "hw:CARD=DX5,DEV=0"
    assert plan.evidence_refs == ("probe:1",)
    for code in (
        ENGINE_GSTREAMER_DIRECT,
        BINDING_ALSA_HW_SELECTED,
        S32_CARRIER_PRESERVES_24_BITS,
        STRICT_NO_RESAMPLE,
        STRICT_NO_REMIX,
        FIXED_VOLUME_SELECTED,
        FALLBACK_STOP,
    ):
        assert code in plan.decision_codes
    assert plan.allow_resample is False
    assert plan.allow_remix is False
    assert plan.allow_processing is False


def test_plan_is_deterministic() -> None:
    planner = OutputPlanner()
    first = planner.plan(_facts())
    second = planner.plan(_facts())
    assert isinstance(first, OutputPlan) and isinstance(second, OutputPlan)
    assert first.plan_id == second.plan_id


def test_16bit_source_uses_s16_carrier() -> None:
    requested = carrier_tuple(_source(bits=16))
    assert requested == PcmTuple(96000, "S16_LE", 2, 16)


def test_no_silent_rate_fallback_192_to_96() -> None:
    """24/192 con evidencia solo de 96k: nunca baja en silencio."""
    refusal = OutputPlanner().plan(
        _facts(source=_source(rate=192000), evidence=(_evidence(rate=96000),))
    )
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == EXACT_TUPLE_UNKNOWN
    assert "192000" in refusal.detail, (
        "el rechazo es del tuple 192k exacto, nunca un plan degradado a 96k"
    )


def test_exact_unsupported_rejection_is_explicit() -> None:
    refusal = OutputPlanner().plan(_facts(evidence=(_evidence(supported=False),)))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == EXACT_TUPLE_UNSUPPORTED


def test_ambiguous_evidence_produces_no_claim() -> None:
    refusal = OutputPlanner().plan(_facts(evidence=(_evidence(supported=None),)))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == EXACT_TUPLE_UNKNOWN


def test_unknown_significant_bits_refused() -> None:
    refusal = OutputPlanner().plan(_facts(source=_source(bits=None)))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == SOURCE_RATE_UNKNOWN


def test_engine_not_gstreamer_refused() -> None:
    refusal = OutputPlanner().plan(_facts(active_engine_id="mpd"))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == ENGINE_NOT_GSTREAMER


def test_missing_selected_device_refused() -> None:
    refusal = OutputPlanner().plan(_facts(selected_device_id=None))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == SELECTED_DEVICE_MISSING


def test_unavailable_device_refused() -> None:
    refusal = OutputPlanner().plan(_facts(device_available=False))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code != ""


def test_no_alsa_hw_binding_refused() -> None:
    assert isinstance(OutputPlanner().plan(_facts(binding=None)), PlannerRefusal)
    unavailable = OutputPlanner().plan(_facts(binding=_binding(available=False)))
    assert isinstance(unavailable, PlannerRefusal)
    assert unavailable.code == NO_ALSA_HW_BINDING


def test_binding_generation_changed_refused() -> None:
    refusal = OutputPlanner().plan(
        _facts(binding=_binding(generation=3), expected_binding_generation=2)
    )
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == BINDING_GENERATION_CHANGED


def test_non_hardware_direct_path_refused() -> None:
    import dataclasses

    profile = stable_direct_preset("p1", DEVICE)
    desktop = dataclasses.replace(profile, path=OutputPathPreference.DESKTOP)
    refusal = OutputPlanner().plan(_facts(profile=desktop))
    assert isinstance(refusal, PlannerRefusal)
    assert refusal.code == PATH_NOT_HARDWARE_DIRECT


def test_sink_spec_consumes_plan_only() -> None:
    plan = OutputPlanner().plan(_facts())
    assert isinstance(plan, OutputPlan)
    spec = sink_spec_for(plan)
    assert spec.factory == "alsasink"
    assert spec.properties == {"device": "hw:CARD=DX5,DEV=0"}


def test_sink_spec_rejects_non_hardware_raw() -> None:
    plan = OutputPlanner().plan(_facts())
    assert isinstance(plan, OutputPlan)
    plugin_plan = OutputPlan(
        plan_id=plan.plan_id,
        stable_device_id=plan.stable_device_id,
        binding=plan.binding,
        path_semantics=PathSemantics.ALSA_PLUGIN,
        requested_pcm=plan.requested_pcm,
        engine_id=plan.engine_id,
        volume_policy=plan.volume_policy,
        allow_resample=plan.allow_resample,
        allow_remix=plan.allow_remix,
        allow_processing=plan.allow_processing,
        fallback=plan.fallback,
        evidence_refs=plan.evidence_refs,
        decision_codes=plan.decision_codes,
    )
    with pytest.raises(ValueError, match="hardware-raw"):
        sink_spec_for(plugin_plan)
