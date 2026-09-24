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

    # §12/§23: the adapted verdict requires the OBSERVED transforming
    # converter with a PROVEN preservation policy.
    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=True,
        noise_shaping_disabled=True,
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
        converter_present=True,
        converter_transforming=True,
        dithering_disabled=True,
        noise_shaping_disabled=True,
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)


def test_pev110r1_02_d1_representation_change_without_observed_mechanism() -> None:
    """§13: AUTHORIZED is not OBSERVED. If the representation changed but no
    converter was observed, preservation cannot be claimed."""
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=False,
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED in snapshot.reasons


def test_pev110r1_02_d2_representation_change_with_unknown_converter_state() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=None,
    )

    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN in snapshot.reasons


def test_pev110r1_02_e2_passthrough_converter_contradicts_the_change() -> None:
    """§15: the endpoint proves the representation changed while the observed
    converter claims it did NOT transform — contradictory evidence."""
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S16_LE", 2, 16),
        requested=PcmTuple(44_100, "S32_LE", 2, 16),
        converter_present=True,
        converter_transforming=False,
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED in snapshot.reasons


def test_pev110r1_02_b2_unchanged_representation_with_passthrough_converter() -> None:
    """§18/§19: an unchanged representation stays DIRECT with a converter that
    proves passthrough — presence alone is never DSP."""
    from michi.domain.signal_truth import SignalTruthVerdict

    pcm = PcmTuple(44_100, "S16_LE", 2, 16)
    snapshot = _preservation_snapshot(
        decoded=pcm,
        requested=pcm,
        effective=pcm,
        alsa=pcm,
        converter_present=True,
        converter_transforming=False,
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT


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
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    snapshot = _preservation_snapshot(
        decoded=PcmTuple(44_100, "S24_3LE", 2, 24),
        requested=PcmTuple(44_100, "S32_LE", 2, 24),
        effective=PcmTuple(44_100, "S32_LE", 2, 16),
    )

    assert snapshot.verdict is not SignalTruthVerdict.DIRECT
    assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH in snapshot.reasons


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


# ── PHASE 3 — REAL GStreamer preservation gate (§26–§32) ───────────────────


def test_pev110r1_03_a_real_audioconvert_readback_proves_policy(tmp_path) -> None:
    """Real GStreamer: read dithering / noise shaping from a LIVE audioconvert.

    The production helper is exercised against a real element and a real
    representation change (S16 -> S32). No hardware sink is used.
    """
    import struct
    import wave

    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    from michi.infrastructure.audio_engines.gstreamer import (
        converter_preservation_config,
    )

    Gst.init(None)

    fixture = tmp_path / "real16.wav"
    with wave.open(str(fixture), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(44_100)
        frames = b"".join(struct.pack("<hh", 1024, -1024) for _ in range(4096))
        handle.writeframes(frames)

    pipeline = Gst.Pipeline.new("r110r1-real-preservation")
    src = Gst.ElementFactory.make("filesrc", "src")
    parser = Gst.ElementFactory.make("wavparse", "parser")
    converter = Gst.ElementFactory.make("audioconvert", "conv")
    caps = Gst.ElementFactory.make("capsfilter", "caps")
    caps.set_property(
        "caps",
        Gst.Caps.from_string(
            "audio/x-raw,format=S32LE,rate=44100,channels=2,layout=interleaved"
        ),
    )
    sink = Gst.ElementFactory.make("fakesink", "sink")
    for element in (src, parser, converter, caps, sink):
        assert element is not None
        pipeline.add(element)
    assert src.link(parser) and parser.link(converter)
    assert converter.link(caps) and caps.link(sink)
    src.set_property("location", str(fixture))

    pipeline.set_state(Gst.State.PAUSED)
    assert pipeline.get_state(5 * Gst.SECOND)[0] is Gst.StateChangeReturn.SUCCESS

    # The REAL element, read through the production helper.
    default_dithering, default_noise = converter_preservation_config(converter)
    assert default_dithering is not None and default_noise is not None

    converter.set_property("dithering", 0)
    converter.set_property("noise-shaping", 0)
    proven = converter_preservation_config(converter)
    assert proven == (True, True), proven

    # Deliberately unsafe: the helper must report the ACTIVE transform policy.
    converter.set_property("dithering", 2)
    assert converter_preservation_config(converter)[0] is False

    # The real representation change (S16 fixture -> S32 caps) is observable.
    sink_pad_caps = caps.get_static_pad("sink").get_current_caps()
    assert sink_pad_caps is not None
    assert "format=(string)S32LE" in sink_pad_caps.to_string()
    upstream_caps = parser.get_static_pad("src").get_current_caps()
    assert upstream_caps is not None
    assert "format=(string)S16LE" in upstream_caps.to_string()

    pipeline.set_state(Gst.State.NULL)
