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


# ── R110R1 §46 — representation-preservation model gates ───────────────────


def _preservation_snapshot(
    *,
    decoded: PcmTuple,
    requested: PcmTuple | None = None,
    effective: PcmTuple | None = None,
    alsa: PcmTuple | None = None,
    converter_present: bool = False,
    converter_transforming: bool | None = None,
    dithering_disabled: bool | None = None,
    noise_shaping_disabled: bool | None = None,
    remix_transforming: bool | None = False,
):
    """Classify one Direct candidate through the productive recorder surface."""
    from michi.domain.audio_evidence import RuntimeTransformEvidence
    from michi.domain.signal_truth import (
        AlsaRuntimeEvidence,
        DecodedRuntimeEvidence,
        EngineRuntimeEvidence,
        OutputPlanEvidence,
        SignalTruthIdentity,
        SignalTruthRecorder,
    )

    identity = SignalTruthIdentity("plan:pev", 1, 1, 1, "usb:dac", "ep:0")
    carrier = requested or (effective or alsa or decoded)
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(identity, carrier, "alsasink", "hw:CARD=AUDIO,DEV=0", True)
    )
    recorder.observe(DecodedRuntimeEvidence(identity, decoded))
    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=effective or carrier,
            sink_factory="alsasink",
            sink_device="hw:CARD=AUDIO,DEV=0",
            graph_factories=("wavparse", "audioconvert", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
            transform_evidence=RuntimeTransformEvidence(
                converter_present=converter_present,
                converter_transforming=converter_transforming,
                remix_transforming=remix_transforming,
                converter_dithering_disabled=dithering_disabled,
                converter_noise_shaping_disabled=noise_shaping_disabled,
            ),
        )
    )
    recorder.observe(
        AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=alsa or carrier,
            access="RW_INTERLEAVED",
            subformat="STD",
            period_size=1024,
            buffer_size=4096,
            proc_path="/proc/asound/card2/pcm0p/sub0/hw_params",
            locator="hw:CARD=AUDIO,DEV=0",
        )
    )
    return recorder.candidate_snapshot


def test_pev110r1_02_a_unchanged_exact_route_is_direct() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    pcm = PcmTuple(44_100, "S16_LE", 2, 16)
    snapshot = _preservation_snapshot(
        decoded=pcm, requested=pcm, effective=pcm, alsa=pcm
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT


def test_pev110r1_02_b_sixteen_to_wide_container_preserved_is_adapted() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_pev110r1_02_c_twenty_four_to_canonical_carrier_preserved_is_adapted() -> None:
    """Canonical §1822 step 6: S32 is the EXACT strict carrier for 24-bit, yet the
    runtime representation changed — the two facts are different dimensions."""
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S24_3LE", 2, 24),
        requested=PcmTuple(44_100, "S32_LE", 2, 24),
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_pev110r1_02_d_wide_container_without_preservation_proof_is_unknown() -> None:
    """No converter evidence at all: the earlier model fabricated S32 precision,
    this one refuses to; the decoded width alone is not a carrier claim."""
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=None,
    )

    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN


def test_pev110r1_02_e_unauthorized_pair_is_never_adapted() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S32_LE", 2, 16),
        requested=PcmTuple(44_100, "S16_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.DSP


def test_pev110r1_02_f_active_dither_is_never_direct() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=False,
        noise_shaping_disabled=True,
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_pev110r1_02_g_active_noise_shaping_is_never_direct() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=True,
        noise_shaping_disabled=False,
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_pev110r1_02_h_transforming_converter_without_policy_is_unknown() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=None,
        noise_shaping_disabled=None,
    )

    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN


def test_pev110r1_02_i_proven_wide_container_policy_is_adapted() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=True,
        noise_shaping_disabled=True,
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_pev110r1_02_j_proven_width_mismatch_is_refuted() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S24_3LE", 2, 24),
        requested=PcmTuple(44_100, "S32_LE", 2, 24),
        effective=PcmTuple(44_100, "S32_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_pev110r1_02_k_rate_mismatch_is_never_direct() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(48_000, "S32_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_pev110r1_02_l_channel_mismatch_is_never_direct() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 6, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
