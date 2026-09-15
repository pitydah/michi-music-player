"""DAC-V35-070 — Signal Truth / runtime evidence gates ST70-01..44."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    RuntimeAnomalyEvidence,
    RuntimeAnomalyKind,
    SignalTruthIdentity,
    SignalTruthReason,
    SignalTruthRecorder,
    SignalTruthVerdict,
    SourceFileFactsEvidence,
)


def _identity(*, execution: int = 1, port: int = 7) -> SignalTruthIdentity:
    return SignalTruthIdentity(
        plan_id="plan-1",
        execution_generation=execution,
        port_generation=port,
        binding_generation=3,
        stable_device_id="usb:2622:0105:DX5ABC123",
        stable_endpoint_signature="ep:dx5:0",
    )


def _pcm(
    rate: int = 96_000,
    fmt: str = "S32_LE",
    channels: int = 2,
    significant_bits: int | None = 24,
) -> PcmTuple:
    return PcmTuple(rate, fmt, channels, significant_bits)


def _plan(identity: SignalTruthIdentity | None = None) -> OutputPlanEvidence:
    return OutputPlanEvidence(
        identity=identity or _identity(),
        requested_pcm=_pcm(),
        sink_factory="alsasink",
        sink_device="hw:CARD=DX5,DEV=0",
        fixed_gain_required=True,
    )


def _engine(
    identity: SignalTruthIdentity | None = None,
    *,
    pcm: PcmTuple | None = None,
    graph: tuple[str, ...] = ("flacdec", "capsfilter", "alsasink"),
    graph_complete: bool = True,
    gain: float | None = 1.0,
    muted: bool | None = False,
    clock: bool | None = True,
    pipeline_clock: bool | None = True,
    slave_method: str | None = "none",
    resampling: bool = False,
    remix: bool = False,
    dsp: bool = False,
    sink_factory: str = "alsasink",
    sink_device: str = "hw:CARD=DX5,DEV=0",
) -> EngineRuntimeEvidence:
    return EngineRuntimeEvidence(
        identity or _identity(),
        pcm or _pcm(),
        sink_factory,
        sink_device,
        graph,
        graph_complete,
        gain,
        muted,
        clock,
        pipeline_clock,
        slave_method,
        resampling,
        remix,
        dsp,
    )


def _alsa(
    identity: SignalTruthIdentity | None = None,
    *,
    pcm: PcmTuple | None = None,
    binding_matches: bool = True,
) -> AlsaRuntimeEvidence:
    return AlsaRuntimeEvidence(
        identity or _identity(),
        pcm or _pcm(),
        "RW_INTERLEAVED",
        "STD",
        1024,
        4096,
        "/proc/asound/card1/pcm0p/sub0/hw_params",
        binding_matches,
    )


def _complete(
    *,
    decoded: PcmTuple | None = None,
    engine: EngineRuntimeEvidence | None = None,
    alsa: AlsaRuntimeEvidence | None = None,
) -> SignalTruthRecorder:
    recorder = SignalTruthRecorder()
    identity = _identity()
    recorder.begin_candidate(_plan(identity))
    recorder.observe(DecodedRuntimeEvidence(identity, decoded or _pcm()))
    recorder.observe(engine or _engine(identity))
    recorder.observe(alsa or _alsa(identity))
    return recorder


def test_st70_01_source_metadata_never_becomes_decoded_runtime() -> None:
    recorder = SignalTruthRecorder()
    identity = _identity()
    recorder.begin_candidate(_plan(identity))

    recorder.observe(
        SourceFileFactsEvidence(
            identity=identity,
            container="flac",
            codec="flac",
            nominal_pcm=_pcm(),
        )
    )

    snapshot = recorder.candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert snapshot.decoded_runtime is None
    assert snapshot.reasons[0] is SignalTruthReason.ST_MISSING_DECODED


def test_st70_02_selected_direct_plan_never_claims_direct() -> None:
    recorder = SignalTruthRecorder()

    recorder.begin_candidate(_plan())

    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert SignalTruthVerdict.DIRECT not in (
        recorder.candidate_snapshot.verdict,
        SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED,
    )


def test_st70_03_engine_sink_caps_are_not_decoded_or_alsa_evidence() -> None:
    recorder = SignalTruthRecorder()
    identity = _identity()
    recorder.begin_candidate(_plan(identity))

    recorder.observe(
        EngineRuntimeEvidence(
            identity=identity,
            effective_pcm=_pcm(),
            sink_factory="alsasink",
            sink_device="hw:CARD=DX5,DEV=0",
            graph_factories=("flacparse", "flacdec", "capsfilter", "alsasink"),
            graph_inspection_complete=True,
            software_gain=1.0,
            muted=False,
            sink_provides_clock=True,
            sink_clock_is_pipeline_clock=True,
            slave_method="none",
        )
    )

    snapshot = recorder.candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert snapshot.decoded_runtime is None
    assert snapshot.device_negotiated is None


def test_st70_04_s32_plan_with_24_bit_metadata_does_not_prove_adaptation() -> None:
    recorder = SignalTruthRecorder()
    identity = _identity()
    recorder.begin_candidate(_plan(identity))
    recorder.observe(
        SourceFileFactsEvidence(identity, "flac", "flac", _pcm(significant_bits=24))
    )
    recorder.observe(DecodedRuntimeEvidence(identity, _pcm(significant_bits=None)))
    recorder.observe(
        EngineRuntimeEvidence(
            identity,
            _pcm(significant_bits=None),
            "alsasink",
            "hw:CARD=DX5,DEV=0",
            ("flacdec", "capsfilter", "alsasink"),
            True,
            1.0,
            False,
            True,
            True,
            "none",
        )
    )

    snapshot = recorder.candidate_snapshot
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    assert SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN in snapshot.reasons


def test_st70_05_evidence_contracts_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _identity().plan_id = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        _engine().software_gain = 0.5  # type: ignore[misc]


def test_st70_06_complete_matching_runtime_is_direct() -> None:
    assert _complete().candidate_snapshot.verdict is SignalTruthVerdict.DIRECT


def test_st70_07_container_adaptation_requires_end_to_end_sbits_proof() -> None:
    identity = _identity()
    recorder = _complete(
        decoded=_pcm(fmt="S24_3LE"),
        engine=_engine(identity, pcm=_pcm(fmt="S32_LE", significant_bits=24)),
        alsa=_alsa(identity, pcm=_pcm(fmt="S32_LE")),
    )
    assert (
        recorder.candidate_snapshot.verdict
        is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    )


def test_st70_08_unknown_sbits_blocks_container_adaptation() -> None:
    identity = _identity()
    recorder = _complete(
        decoded=_pcm(fmt="S24_3LE", significant_bits=None),
        engine=_engine(identity, pcm=_pcm(fmt="S32_LE", significant_bits=None)),
        alsa=_alsa(identity, pcm=_pcm(fmt="S32_LE", significant_bits=None)),
    )
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.UNKNOWN


def test_st70_09_observed_resampling_is_resampled() -> None:
    recorder = _complete(engine=_engine(resampling=True))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.RESAMPLED
    clock_resample = _complete(engine=_engine(slave_method="resample"))
    assert clock_resample.candidate_snapshot.verdict is SignalTruthVerdict.RESAMPLED


def test_st70_10_unexplained_alsa_rate_mismatch_is_contradicted() -> None:
    recorder = _complete(alsa=_alsa(pcm=_pcm(rate=48_000)))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert (
        SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION
        in recorder.candidate_snapshot.reasons
    )


def test_st70_11_explicit_remix_is_remixed() -> None:
    recorder = _complete(engine=_engine(remix=True))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.REMIXED


def test_st70_12_unexplained_alsa_channel_mismatch_is_contradicted() -> None:
    recorder = _complete(alsa=_alsa(pcm=_pcm(channels=6)))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_st70_13_observed_dsp_is_dsp() -> None:
    recorder = _complete(engine=_engine(dsp=True))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.DSP
    endian_change = _complete(
        decoded=_pcm(fmt="S16_LE", significant_bits=16),
        engine=_engine(pcm=_pcm(fmt="S16_BE", significant_bits=16)),
        alsa=_alsa(pcm=_pcm(fmt="S16_BE", significant_bits=16)),
    )
    assert endian_change.candidate_snapshot.verdict is SignalTruthVerdict.DSP


def test_st70_14_contradiction_precedes_transformation() -> None:
    recorder = _complete(
        engine=_engine(
            graph=("audioresample", "alsasink"),
            dsp=True,
            sink_device="hw:CARD=OTHER,DEV=0",
        )
    )
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.CONTRADICTED


def test_st70_15_resampled_precedes_remixed_and_dsp() -> None:
    recorder = _complete(engine=_engine(resampling=True, remix=True, dsp=True))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.RESAMPLED


def test_st70_16_reason_order_is_deterministic() -> None:
    recorder = _complete(
        engine=_engine(sink_factory="autoaudiosink", sink_device="default", gain=0.5)
    )
    assert recorder.candidate_snapshot.reasons == (
        SignalTruthReason.ST_DEVICE_MISMATCH,
        SignalTruthReason.ST_SINK_MISMATCH,
        SignalTruthReason.ST_GAIN_NOT_UNITY,
    )


def test_st70_17_sink_device_mismatch_is_contradicted() -> None:
    recorder = _complete(engine=_engine(sink_device="hw:CARD=OTHER,DEV=0"))
    assert (
        recorder.candidate_snapshot.reasons[0] is SignalTruthReason.ST_DEVICE_MISMATCH
    )


def test_st70_18_sink_factory_mismatch_is_contradicted() -> None:
    recorder = _complete(engine=_engine(sink_factory="pipewiresink"))
    assert SignalTruthReason.ST_SINK_MISMATCH in recorder.candidate_snapshot.reasons


def test_st70_19_non_unity_fixed_gain_is_contradicted() -> None:
    recorder = _complete(engine=_engine(gain=0.75))
    assert SignalTruthReason.ST_GAIN_NOT_UNITY in recorder.candidate_snapshot.reasons


def test_st70_20_runtime_error_is_contradicted() -> None:
    recorder = _complete()
    recorder.observe(
        RuntimeAnomalyEvidence(_identity(), RuntimeAnomalyKind.ERROR, "boom")
    )
    assert recorder.candidate_snapshot.reasons[0] is SignalTruthReason.ST_RUNTIME_ERROR


def test_st70_21_xrun_is_contradicted() -> None:
    recorder = _complete()
    recorder.observe(
        RuntimeAnomalyEvidence(_identity(), RuntimeAnomalyKind.XRUN, "xrun")
    )
    assert recorder.candidate_snapshot.reasons[0] is SignalTruthReason.ST_XRUN


def test_st70_22_missing_engine_effective_is_unknown() -> None:
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan())
    recorder.observe(DecodedRuntimeEvidence(_identity(), _pcm()))
    recorder.observe(_alsa())
    assert (
        SignalTruthReason.ST_MISSING_ENGINE_EFFECTIVE
        in recorder.candidate_snapshot.reasons
    )


def test_st70_23_missing_alsa_is_unknown() -> None:
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan())
    recorder.observe(DecodedRuntimeEvidence(_identity(), _pcm()))
    recorder.observe(_engine())
    assert SignalTruthReason.ST_MISSING_ALSA in recorder.candidate_snapshot.reasons


def test_st70_24_incomplete_graph_is_unknown() -> None:
    recorder = _complete(engine=_engine(graph_complete=False))
    assert SignalTruthReason.ST_MISSING_GRAPH in recorder.candidate_snapshot.reasons


def test_st70_25_missing_gain_is_unknown() -> None:
    recorder = _complete(engine=_engine(gain=None))
    assert SignalTruthReason.ST_MISSING_GAIN in recorder.candidate_snapshot.reasons


def test_st70_26_missing_clock_policy_is_unknown() -> None:
    recorder = _complete(engine=_engine(slave_method=None))
    assert SignalTruthReason.ST_MISSING_CLOCK in recorder.candidate_snapshot.reasons
    invalid = _complete(engine=_engine(clock=False, pipeline_clock=False))
    assert invalid.candidate_snapshot.verdict is SignalTruthVerdict.CONTRADICTED
    assert (
        SignalTruthReason.ST_CLOCK_POLICY_MISMATCH in invalid.candidate_snapshot.reasons
    )


def test_st70_27_candidate_does_not_replace_active_truth() -> None:
    recorder = _complete()
    recorder.commit_candidate(_identity())
    active = recorder.active_snapshot
    next_identity = _identity(execution=2, port=8)
    recorder.begin_candidate(_plan(next_identity))
    assert recorder.active_snapshot is active
    assert recorder.candidate_snapshot.identity == next_identity
    assert recorder.commit_candidate(next_identity) is False
    assert recorder.active_snapshot is active


def test_st70_28_commit_promotes_exact_candidate() -> None:
    recorder = _complete()
    assert recorder.commit_candidate(_identity()) is True
    assert recorder.active_snapshot is not None
    assert recorder.active_snapshot.verdict is SignalTruthVerdict.DIRECT


def test_st70_29_same_plan_stale_generation_event_is_discarded() -> None:
    recorder = SignalTruthRecorder()
    current = _identity(execution=2, port=8)
    recorder.begin_candidate(_plan(current))
    assert recorder.observe(DecodedRuntimeEvidence(_identity(), _pcm())) is False
    assert recorder.candidate_snapshot.decoded_runtime is None


def test_st70_30_destructive_boundary_retires_old_without_promoting_new() -> None:
    recorder = _complete()
    recorder.commit_candidate(_identity())
    next_identity = _identity(execution=2, port=8)
    recorder.begin_candidate(_plan(next_identity))
    assert recorder.retire_active(_identity()) is True
    assert recorder.active_snapshot is None
    assert recorder.candidate_snapshot.identity == next_identity


def test_st70_31_predestructive_abort_preserves_active_truth() -> None:
    recorder = _complete()
    recorder.commit_candidate(_identity())
    active = recorder.active_snapshot
    candidate = _identity(execution=2, port=8)
    recorder.begin_candidate(_plan(candidate))
    recorder.discard_candidate(candidate)
    assert recorder.active_snapshot is active


def test_st70_32_termination_clears_only_matching_active_truth() -> None:
    recorder = _complete()
    recorder.commit_candidate(_identity())
    assert recorder.terminate(_identity(execution=99)) is False
    assert recorder.active_snapshot is not None
    assert recorder.terminate(_identity()) is True
    assert recorder.active_snapshot is None


def test_st70_33_mute_is_separate_from_unity_gain() -> None:
    recorder = _complete(engine=_engine(muted=True, gain=1.0))
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.DIRECT
    assert recorder.candidate_snapshot.engine_effective.muted is True
    assert recorder.candidate_snapshot.engine_effective.software_gain == 1.0


def test_st70_34_binding_readback_mismatch_is_contradicted() -> None:
    recorder = _complete(alsa=_alsa(binding_matches=False))
    assert SignalTruthReason.ST_BINDING_MISMATCH in recorder.candidate_snapshot.reasons


def test_observer_failure_cannot_break_recorder_state_commit() -> None:
    recorder = SignalTruthRecorder()
    recorder.subscribe(lambda: (_ for _ in ()).throw(RuntimeError("observer failed")))
    recorder.begin_candidate(_plan())
    assert recorder.candidate_snapshot.verdict is SignalTruthVerdict.UNKNOWN
