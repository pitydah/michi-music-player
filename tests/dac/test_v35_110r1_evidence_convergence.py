"""DAC-V35-110R1 — physical evidence completion & Signal Truth convergence gates.

- ``pev110r1_01_*`` strict/compatible carrier policy coherence
- ``pev110r1_02_*`` productive Signal Truth convergence
- ``pev110r1_03_*`` success/failure state hygiene
"""

from __future__ import annotations

from michi.application.carrier_resolution import (
    CandidateCarrierResolver,
    CarrierAdaptationKind,
)
from michi.domain.audio_evidence import DecodedSourceSignal, PcmTuple
from michi.domain.audio_output import OutputPathPreference, is_strict_direct_path
from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

# ── shared fixtures ────────────────────────────────────────────────────────


def _source(bits: int, *, rate: int = 44_100) -> DecodedSourceSignal:
    return DecodedSourceSignal("PCM", rate, bits, 2, None)


def _plan(*, bits: int, adaptation: str, fmt: str, rate: int = 44_100):
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_output import (
        FallbackKind,
        GstSinkSpec,
        OutputPlan,
        PathSemantics,
        VolumePolicy,
    )

    carrier = "S32_LE" if bits == 24 or adaptation != "exact" else "S16_LE"
    return OutputPlan(
        plan_id=f"plan:{fmt}:{bits}:{adaptation}",
        stable_device_id="usb:152a:85dd:3-3.3.2",
        binding=AudioDeviceBinding(
            kind=BindingKind.ALSA_PCM,
            locator="hw:CARD=AUDIO,DEV=0",
            generation=1,
            currently_available=True,
            card_index=2,
            pcm_device=0,
        ),
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(rate, carrier, 2, bits),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec("alsasink", "hw:CARD=AUDIO,DEV=0"),
        resync_delay_ms=0,
        preconditions=(),
        evidence_refs=(),
        decision_codes=(),
        carrier_adaptation=adaptation,
    )


# ── Phase 1 — strict/compatible carrier policy coherence ───────────────────


def test_pev110r1_01_a_strict_candidates_are_exact_only() -> None:
    """Strict Direct must never offer an adaptation candidate."""
    resolver = CandidateCarrierResolver()
    for bits in (16, 24):
        strict = resolver.candidates(_source(bits), allow_adaptation=False)
        assert all(item.is_exact for item in strict), bits
        assert all(
            item.adaptation_kind is CarrierAdaptationKind.EXACT for item in strict
        ), bits


def test_pev110r1_01_b_compatible_adds_bounded_widening_only() -> None:
    resolver = CandidateCarrierResolver()

    # 16-bit: the narrow carrier is the exact target and S32_LE is the
    # bounded compatible widening.
    sixteen = resolver.candidates(_source(16), allow_adaptation=True)
    assert sixteen[0].is_exact
    widened = [
        item
        for item in sixteen
        if item.adaptation_kind is CarrierAdaptationKind.CONTAINER_WIDTH
    ]
    assert widened
    assert all(item.tuple.significant_bits == 16 for item in widened)

    # 24-bit: the S32 carrier IS the canonical exact target (§1822 step 6), so
    # no compatible-only widening is required for the proven precision.
    twenty_four = resolver.candidates(_source(24), allow_adaptation=True)
    assert [item.adaptation_kind for item in twenty_four] == [
        CarrierAdaptationKind.EXACT
    ]
    for items in (sixteen, twenty_four):
        assert len(items) <= resolver.MAX_CANDIDATES


def test_pev110r1_01_c_canonical_exact_carrier_for_twenty_four_bits_is_s32() -> None:
    """Canonical §1822 step 6: the S32 carrier for a 24-bit source IS exact."""
    resolver = CandidateCarrierResolver()
    exact = resolver.candidates(_source(24), allow_adaptation=False)[0]

    assert exact.tuple.transport_format == "S32_LE"
    assert exact.adaptation_kind is CarrierAdaptationKind.EXACT
    assert exact.tuple.significant_bits == 24


def test_pev110r1_01_d_recipe_declares_the_container_preservation_policy() -> None:
    """The plan carries the carrier POLICY; the recipe carries the transport
    preservation policy (§292). An exact 24-bit plan whose container is wider
    than the proven precision still needs the explicit converter policy."""
    exact24 = recipe_from_plan(_plan(bits=24, adaptation="exact", fmt="S32_LE"))
    assert exact24.container_conversion is True
    assert exact24.gst_format == "S32LE"

    exact16 = recipe_from_plan(_plan(bits=16, adaptation="exact", fmt="S16_LE"))
    assert exact16.container_conversion is False

    adapted16 = recipe_from_plan(
        _plan(bits=16, adaptation="container_width", fmt="S16_LE")
    )
    assert adapted16.container_conversion is True


def test_pev110r1_01_e_declared_conversion_is_authorized_undeclared_is_not() -> None:
    """An UNDECLARED transforming converter stays fail-closed; a declared one
    is the §292 explicit preservation policy and is accepted."""
    from dataclasses import replace

    from michi.domain.signal_truth import RuntimeTransformEvidence
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
        validate_runtime,
    )
    from tests.dac.test_v35_runtime_inspector import _snapshot

    # A COMPLETE observation: the converter is present and transforming, and
    # the remix state is known. An unknown activity state stays fail-closed.
    evidence = RuntimeTransformEvidence(
        converter_present=True,
        converter_transforming=True,
        remix_transforming=False,
    )
    recipe = recipe_from_plan(_plan(bits=24, adaptation="exact", fmt="S32_LE"))

    # Declared policy: authorized (Signal Truth reports the representation
    # change separately).
    validate_runtime(
        replace(recipe, container_conversion=True),
        _snapshot(
            plan_id=recipe.plan_id,
            sink_device=recipe.device,
            negotiated_rate_hz=recipe.rate_hz,
            negotiated_channels=recipe.channels,
            transform_evidence=evidence,
        ),
    )

    # Undeclared: refused, exactly as the silent-widening contract requires.
    import pytest

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(
            replace(recipe, container_conversion=False),
            _snapshot(
                plan_id=recipe.plan_id,
                sink_device=recipe.device,
                negotiated_rate_hz=recipe.rate_hz,
                negotiated_channels=recipe.channels,
                transform_evidence=evidence,
            ),
        )
    assert exc_info.value.code == "DIRECT_CONVERTER_ACTIVE"


def test_pev110r1_01_f_strict_path_helper_matches_the_policy() -> None:
    assert is_strict_direct_path(OutputPathPreference.HARDWARE_DIRECT) is True
    assert (
        is_strict_direct_path(OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE) is False
    )
