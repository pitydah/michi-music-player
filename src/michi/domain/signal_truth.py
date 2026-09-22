"""DAC-V35-070 Signal Truth contracts and evidence-first classifier.

The recorder is deliberately passive: adapters submit immutable normalized
events and lifecycle owners move candidate/active truth.  It performs no I/O
and consults no other authority.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from enum import Enum

from michi.domain.audio_evidence import PcmTuple, RuntimeTransformEvidence


class SignalTruthVerdict(Enum):
    DIRECT = "direct"
    DIRECT_CONTAINER_ADAPTED = "direct_container_adapted"
    DSP = "dsp"
    RESAMPLED = "resampled"
    REMIXED = "remixed"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class SignalTruthReason(Enum):
    ST_DEVICE_MISMATCH = "ST_DEVICE_MISMATCH"
    ST_BINDING_MISMATCH = "ST_BINDING_MISMATCH"
    ST_SINK_MISMATCH = "ST_SINK_MISMATCH"
    ST_RUNTIME_ERROR = "ST_RUNTIME_ERROR"
    ST_XRUN = "ST_XRUN"
    ST_GAIN_NOT_UNITY = "ST_GAIN_NOT_UNITY"
    ST_CLOCK_POLICY_MISMATCH = "ST_CLOCK_POLICY_MISMATCH"
    ST_ALSA_NEGOTIATION_CONTRADICTION = "ST_ALSA_NEGOTIATION_CONTRADICTION"
    ST_RESAMPLER_PRESENT = "ST_RESAMPLER_PRESENT"
    ST_RATE_MISMATCH = "ST_RATE_MISMATCH"
    ST_REMIX_OBSERVED = "ST_REMIX_OBSERVED"
    ST_CHANNEL_MISMATCH = "ST_CHANNEL_MISMATCH"
    ST_DSP_PRESENT = "ST_DSP_PRESENT"
    ST_CONTAINER_ADAPTED = "ST_CONTAINER_ADAPTED"
    ST_MISSING_DECODED = "ST_MISSING_DECODED"
    ST_MISSING_ENGINE_EFFECTIVE = "ST_MISSING_ENGINE_EFFECTIVE"
    ST_MISSING_ALSA = "ST_MISSING_ALSA"
    ST_MISSING_GRAPH = "ST_MISSING_GRAPH"
    ST_MISSING_GAIN = "ST_MISSING_GAIN"
    ST_MISSING_CLOCK = "ST_MISSING_CLOCK"
    ST_SIGNIFICANT_BITS_UNKNOWN = "ST_SIGNIFICANT_BITS_UNKNOWN"
    ST_CONVERTER_STATE_UNKNOWN = "ST_CONVERTER_STATE_UNKNOWN"
    ST_RESAMPLER_STATE_UNKNOWN = "ST_RESAMPLER_STATE_UNKNOWN"
    ST_SOURCE_DECODED_MISMATCH = "ST_SOURCE_DECODED_MISMATCH"


@dataclass(frozen=True, slots=True)
class SignalTruthIdentity:
    plan_id: str
    execution_generation: int
    port_generation: int
    binding_generation: int
    stable_device_id: str
    stable_endpoint_signature: str | None


@dataclass(frozen=True, slots=True)
class OutputPlanEvidence:
    identity: SignalTruthIdentity
    requested_pcm: PcmTuple
    sink_factory: str
    sink_device: str
    fixed_gain_required: bool


@dataclass(frozen=True, slots=True)
class SourceFileFactsEvidence:
    identity: SignalTruthIdentity
    container: str | None
    codec: str | None
    nominal_pcm: PcmTuple | None


@dataclass(frozen=True, slots=True)
class DecodedRuntimeEvidence:
    identity: SignalTruthIdentity
    pcm: PcmTuple


@dataclass(frozen=True, slots=True)
class EngineRuntimeEvidence:
    identity: SignalTruthIdentity
    effective_pcm: PcmTuple | None
    sink_factory: str
    sink_device: str
    graph_factories: tuple[str, ...]
    graph_inspection_complete: bool
    software_gain: float | None
    muted: bool | None
    sink_provides_clock: bool | None
    sink_clock_is_pipeline_clock: bool | None
    slave_method: str | None
    resampling_observed: bool = False
    remix_observed: bool = False
    dsp_observed: bool = False
    transform_evidence: RuntimeTransformEvidence = RuntimeTransformEvidence()


@dataclass(frozen=True, slots=True)
class AlsaRuntimeEvidence:
    identity: SignalTruthIdentity
    negotiated_pcm: PcmTuple
    access: str | None
    subformat: str | None
    period_size: int | None
    buffer_size: int | None
    proc_path: str
    binding_matches: bool = True
    card_index: int | None = None
    pcm_device: int | None = None
    pcm_subdevice: int | None = None
    locator: str | None = None
    stable_endpoint_signature: str | None = None
    binding_generation: int | None = None


class RuntimeAnomalyKind(Enum):
    ERROR = "error"
    XRUN = "xrun"
    BINDING_MISMATCH = "binding_mismatch"


@dataclass(frozen=True, slots=True)
class RuntimeAnomalyEvidence:
    identity: SignalTruthIdentity
    kind: RuntimeAnomalyKind
    detail: str | None = None


SignalTruthEvidence = (
    SourceFileFactsEvidence
    | DecodedRuntimeEvidence
    | EngineRuntimeEvidence
    | AlsaRuntimeEvidence
    | RuntimeAnomalyEvidence
)


@dataclass(frozen=True, slots=True)
class SignalTruthSnapshot:
    identity: SignalTruthIdentity
    plan: OutputPlanEvidence
    source_file_facts: SourceFileFactsEvidence | None
    decoded_runtime: DecodedRuntimeEvidence | None
    engine_effective: EngineRuntimeEvidence | None
    device_negotiated: AlsaRuntimeEvidence | None
    anomalies: tuple[RuntimeAnomalyEvidence, ...]
    verdict: SignalTruthVerdict
    reasons: tuple[SignalTruthReason, ...]


_CONTRADICTION_ORDER = (
    SignalTruthReason.ST_DEVICE_MISMATCH,
    SignalTruthReason.ST_BINDING_MISMATCH,
    SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION,
    SignalTruthReason.ST_SINK_MISMATCH,
    SignalTruthReason.ST_RUNTIME_ERROR,
    SignalTruthReason.ST_XRUN,
    SignalTruthReason.ST_GAIN_NOT_UNITY,
    SignalTruthReason.ST_CLOCK_POLICY_MISMATCH,
)
_UNKNOWN_ORDER = (
    SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN,
    SignalTruthReason.ST_RESAMPLER_STATE_UNKNOWN,
    SignalTruthReason.ST_MISSING_DECODED,
    SignalTruthReason.ST_MISSING_ENGINE_EFFECTIVE,
    SignalTruthReason.ST_MISSING_ALSA,
    SignalTruthReason.ST_MISSING_GRAPH,
    SignalTruthReason.ST_MISSING_GAIN,
    SignalTruthReason.ST_MISSING_CLOCK,
    SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN,
)


def _ordered(found: set[SignalTruthReason], order) -> tuple[SignalTruthReason, ...]:
    return tuple(reason for reason in order if reason in found)


#: Lossless integer containers authorized per PROVEN signal width. A carrier
#: drawn from this set transports the same significant value exactly (the
#: narrower samples are left-shifted into the wider container with zero fill);
#: anything else is a real transform and must never be reported as adapted.
_LOSSLESS_CONTAINERS_BY_SIGNIFICANT_BITS: dict[int, frozenset[str]] = {
    16: frozenset({"S16LE", "S32LE"}),
    24: frozenset({"S243LE", "S2432LE", "S32LE"}),
}


def _lossless_container_adaptation(
    requested_pcm: PcmTuple,
    decoded_pcm: PcmTuple,
    negotiated_formats: set[str],
) -> bool:
    """True only when the PLAN authorized a wider lossless container.

    The plan is the policy authority: strict Direct never requests a carrier
    whose transport format differs from the decoded source, so a format
    difference can only be a policy-authorized container-width adaptation when
    the requested carrier is the wider authorized container for the SAME
    proven width, rate and channel count.
    """
    bits = decoded_pcm.significant_bits
    allowed = _LOSSLESS_CONTAINERS_BY_SIGNIFICANT_BITS.get(bits)
    if allowed is None:
        return False
    requested_format = requested_pcm.transport_format.replace("_", "").upper()
    decoded_format = decoded_pcm.transport_format.replace("_", "").upper()
    if requested_format not in allowed:
        return False
    if requested_format == decoded_format:
        # The plan asked for the source-native carrier: any negotiated format
        # difference is then an unauthorized transform, not an adaptation.
        return False
    if requested_pcm.significant_bits != bits:
        return False
    if requested_pcm.rate_hz != decoded_pcm.rate_hz:
        return False
    if requested_pcm.channels != decoded_pcm.channels:
        return False
    return negotiated_formats <= allowed


def classify_signal_truth(snapshot: SignalTruthSnapshot) -> SignalTruthSnapshot:
    """Return ``snapshot`` with deterministic fail-closed verdict and reasons."""
    plan = snapshot.plan
    decoded = snapshot.decoded_runtime
    engine = snapshot.engine_effective
    alsa = snapshot.device_negotiated

    provenance: tuple[SignalTruthReason, ...] = ()
    source = snapshot.source_file_facts
    if source is not None and source.nominal_pcm is not None and decoded is not None:
        nominal = source.nominal_pcm
        runtime = decoded.pcm
        if (
            nominal.rate_hz != runtime.rate_hz
            or nominal.channels != runtime.channels
            or (
                nominal.significant_bits is not None
                and runtime.significant_bits is not None
                and nominal.significant_bits != runtime.significant_bits
            )
        ):
            provenance = (SignalTruthReason.ST_SOURCE_DECODED_MISMATCH,)

    def result(verdict, reasons=()):
        return replace(snapshot, verdict=verdict, reasons=(*reasons, *provenance))

    transforms = (
        engine.transform_evidence if engine is not None else RuntimeTransformEvidence()
    )
    resampling_observed = bool(
        engine is not None
        and (
            engine.resampling_observed
            or transforms.resampler_transforming is True
            or engine.slave_method == "resample"
        )
    )
    remix_observed = bool(
        engine is not None
        and (engine.remix_observed or transforms.remix_transforming is True)
    )

    contradictions: set[SignalTruthReason] = set()
    if engine is not None:
        if engine.graph_inspection_complete and engine.sink_device != plan.sink_device:
            contradictions.add(SignalTruthReason.ST_DEVICE_MISMATCH)
        if (
            engine.graph_inspection_complete
            and engine.sink_factory != plan.sink_factory
        ):
            contradictions.add(SignalTruthReason.ST_SINK_MISMATCH)
        if plan.fixed_gain_required and engine.software_gain not in (None, 1.0):
            contradictions.add(SignalTruthReason.ST_GAIN_NOT_UNITY)
    if alsa is not None and not alsa.binding_matches:
        contradictions.add(SignalTruthReason.ST_BINDING_MISMATCH)
    if (
        decoded is not None
        and engine is not None
        and engine.effective_pcm is not None
        and alsa is not None
    ):
        requested = plan.requested_pcm
        effective = engine.effective_pcm
        negotiated = alsa.negotiated_pcm
        software_rate_matches = (
            decoded.pcm.rate_hz == effective.rate_hz == requested.rate_hz
        )
        software_channels_match = (
            decoded.pcm.channels == effective.channels == requested.channels
        )
        if (
            software_rate_matches
            and effective.rate_hz != negotiated.rate_hz
            and not resampling_observed
        ) or (
            software_channels_match
            and effective.channels != negotiated.channels
            and not remix_observed
        ):
            contradictions.add(SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION)
    if engine is not None and (
        engine.sink_provides_clock is False
        or engine.sink_clock_is_pipeline_clock is False
    ):
        contradictions.add(SignalTruthReason.ST_CLOCK_POLICY_MISMATCH)
    for anomaly in snapshot.anomalies:
        if anomaly.kind is RuntimeAnomalyKind.BINDING_MISMATCH:
            contradictions.add(SignalTruthReason.ST_BINDING_MISMATCH)
        elif anomaly.kind is RuntimeAnomalyKind.ERROR:
            contradictions.add(SignalTruthReason.ST_RUNTIME_ERROR)
        else:
            contradictions.add(SignalTruthReason.ST_XRUN)
    if contradictions:
        return result(
            SignalTruthVerdict.CONTRADICTED,
            _ordered(contradictions, _CONTRADICTION_ORDER),
        )

    transformed: set[SignalTruthReason] = set()
    if engine is not None:
        if resampling_observed:
            transformed.add(SignalTruthReason.ST_RESAMPLER_PRESENT)
        if remix_observed:
            transformed.add(SignalTruthReason.ST_REMIX_OBSERVED)
        converter_changed_without_endpoint_delta = bool(
            transforms.converter_transforming is True
            and decoded is not None
            and engine.effective_pcm is not None
            and decoded.pcm.transport_format.replace("_", "").upper()
            == engine.effective_pcm.transport_format.replace("_", "").upper()
            and not remix_observed
        )
        if engine.dsp_observed or converter_changed_without_endpoint_delta:
            transformed.add(SignalTruthReason.ST_DSP_PRESENT)
    if (
        decoded is not None
        and engine is not None
        and engine.effective_pcm is not None
        and alsa is not None
    ):
        if (
            resampling_observed
            and len(
                {
                    decoded.pcm.rate_hz,
                    engine.effective_pcm.rate_hz,
                    alsa.negotiated_pcm.rate_hz,
                }
            )
            != 1
        ):
            transformed.add(SignalTruthReason.ST_RATE_MISMATCH)
        if (
            remix_observed
            and len(
                {
                    decoded.pcm.channels,
                    engine.effective_pcm.channels,
                    alsa.negotiated_pcm.channels,
                }
            )
            != 1
        ):
            transformed.add(SignalTruthReason.ST_CHANNEL_MISMATCH)
    if transformed:
        if transformed & {
            SignalTruthReason.ST_RESAMPLER_PRESENT,
            SignalTruthReason.ST_RATE_MISMATCH,
        }:
            verdict = SignalTruthVerdict.RESAMPLED
        elif transformed & {
            SignalTruthReason.ST_REMIX_OBSERVED,
            SignalTruthReason.ST_CHANNEL_MISMATCH,
        }:
            verdict = SignalTruthVerdict.REMIXED
        else:
            verdict = SignalTruthVerdict.DSP
        transform_order = (
            SignalTruthReason.ST_RESAMPLER_PRESENT,
            SignalTruthReason.ST_RATE_MISMATCH,
            SignalTruthReason.ST_REMIX_OBSERVED,
            SignalTruthReason.ST_CHANNEL_MISMATCH,
            SignalTruthReason.ST_DSP_PRESENT,
        )
        return result(verdict, _ordered(transformed, transform_order))

    transform_unknown: set[SignalTruthReason] = set()
    if engine is not None:
        if transforms.converter_present and (
            transforms.converter_transforming is None
            or transforms.remix_transforming is None
        ):
            transform_unknown.add(SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN)
        if transforms.resampler_present and transforms.resampler_transforming is None:
            transform_unknown.add(SignalTruthReason.ST_RESAMPLER_STATE_UNKNOWN)
    if transform_unknown:
        return result(
            SignalTruthVerdict.UNKNOWN,
            _ordered(transform_unknown, _UNKNOWN_ORDER),
        )

    missing: set[SignalTruthReason] = set()
    if decoded is None:
        missing.add(SignalTruthReason.ST_MISSING_DECODED)
    if engine is None or engine.effective_pcm is None:
        missing.add(SignalTruthReason.ST_MISSING_ENGINE_EFFECTIVE)
    if alsa is None:
        missing.add(SignalTruthReason.ST_MISSING_ALSA)
    if (
        engine is None
        or not engine.graph_inspection_complete
        or "__inspection_failed__" in engine.graph_factories
    ):
        missing.add(SignalTruthReason.ST_MISSING_GRAPH)
    if engine is None or engine.software_gain is None:
        missing.add(SignalTruthReason.ST_MISSING_GAIN)
    if (
        engine is None
        or engine.sink_provides_clock is None
        or engine.sink_clock_is_pipeline_clock is None
        or engine.slave_method is None
    ):
        missing.add(SignalTruthReason.ST_MISSING_CLOCK)
    if (
        decoded is not None
        and decoded.pcm.significant_bits is None
        or engine is not None
        and engine.effective_pcm is not None
        and engine.effective_pcm.significant_bits is None
        or alsa is not None
        and alsa.negotiated_pcm.significant_bits is None
    ):
        missing.add(SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN)
    if missing:
        return result(SignalTruthVerdict.UNKNOWN, _ordered(missing, _UNKNOWN_ORDER))

    assert decoded is not None and engine is not None and alsa is not None
    assert engine.effective_pcm is not None
    signals = (decoded.pcm, engine.effective_pcm, alsa.negotiated_pcm)
    rates = {item.rate_hz for item in signals}
    channels = {item.channels for item in signals}
    significant_bits = {
        decoded.pcm.significant_bits,
        engine.effective_pcm.significant_bits,
        alsa.negotiated_pcm.significant_bits,
    }
    if len(rates) != 1:
        reason = (
            SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION
            if engine.effective_pcm.rate_hz != alsa.negotiated_pcm.rate_hz
            else SignalTruthReason.ST_RATE_MISMATCH
        )
        return result(SignalTruthVerdict.CONTRADICTED, (reason,))
    if len(channels) != 1:
        reason = (
            SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION
            if engine.effective_pcm.channels != alsa.negotiated_pcm.channels
            else SignalTruthReason.ST_CHANNEL_MISMATCH
        )
        return result(SignalTruthVerdict.CONTRADICTED, (reason,))
    if len(significant_bits) != 1:
        return result(
            SignalTruthVerdict.UNKNOWN,
            (SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN,),
        )
    formats = {item.transport_format.replace("_", "").upper() for item in signals}
    if len(formats) != 1:
        if _lossless_container_adaptation(plan.requested_pcm, decoded.pcm, formats):
            return result(
                SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED,
                (SignalTruthReason.ST_CONTAINER_ADAPTED,),
            )
        return result(SignalTruthVerdict.DSP, (SignalTruthReason.ST_DSP_PRESENT,))
    return result(SignalTruthVerdict.DIRECT)


def _initial_snapshot(plan: OutputPlanEvidence) -> SignalTruthSnapshot:
    return classify_signal_truth(
        SignalTruthSnapshot(
            identity=plan.identity,
            plan=plan,
            source_file_facts=None,
            decoded_runtime=None,
            engine_effective=None,
            device_negotiated=None,
            anomalies=(),
            verdict=SignalTruthVerdict.UNKNOWN,
            reasons=(),
        )
    )


class SignalTruthRecorder:
    """One passive candidate/active runtime evidence recorder."""

    def __init__(self) -> None:
        self._candidate: SignalTruthSnapshot | None = None
        self._active: SignalTruthSnapshot | None = None
        self._last: SignalTruthSnapshot | None = None
        self._subscribers: list[Callable[[], None]] = []

    @property
    def candidate_snapshot(self) -> SignalTruthSnapshot:
        if self._candidate is None:
            raise RuntimeError("no Signal Truth candidate")
        return self._candidate

    @property
    def active_snapshot(self) -> SignalTruthSnapshot | None:
        return self._active

    @property
    def last_snapshot(self) -> SignalTruthSnapshot | None:
        return self._last

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def begin_candidate(self, plan: OutputPlanEvidence) -> None:
        if self._candidate is not None and self._candidate.identity != plan.identity:
            self._last = self._candidate
        self._candidate = _initial_snapshot(plan)
        self._publish()

    def observe(self, event: SignalTruthEvidence) -> bool:
        if self._candidate is not None and event.identity == self._candidate.identity:
            self._candidate = self._with_event(self._candidate, event)
            self._publish()
            return True
        if self._active is not None and event.identity == self._active.identity:
            self._active = self._with_event(self._active, event)
            self._publish()
            return True
        return False

    def commit_candidate(self, identity: SignalTruthIdentity) -> bool:
        if (
            self._candidate is None
            or self._candidate.identity != identity
            or self._active is not None
        ):
            return False
        self._active = self._candidate
        self._candidate = None
        self._publish()
        return True

    def discard_candidate(self, identity: SignalTruthIdentity) -> bool:
        if self._candidate is None or self._candidate.identity != identity:
            return False
        self._last = self._candidate
        self._candidate = None
        self._publish()
        return True

    def retire_active(self, identity: SignalTruthIdentity) -> bool:
        if self._active is None or self._active.identity != identity:
            return False
        self._last = self._active
        self._active = None
        self._publish()
        return True

    def terminate(self, identity: SignalTruthIdentity) -> bool:
        changed = False
        if self._candidate is not None and self._candidate.identity == identity:
            self._last = self._candidate
            self._candidate = None
            changed = True
        if self._active is not None and self._active.identity == identity:
            self._last = self._active
            self._active = None
            changed = True
        if changed:
            self._publish()
        return changed

    @staticmethod
    def _with_event(
        snapshot: SignalTruthSnapshot, event: SignalTruthEvidence
    ) -> SignalTruthSnapshot:
        if isinstance(event, SourceFileFactsEvidence):
            updated = replace(snapshot, source_file_facts=event)
        elif isinstance(event, DecodedRuntimeEvidence):
            updated = replace(snapshot, decoded_runtime=event)
        elif isinstance(event, EngineRuntimeEvidence):
            updated = replace(snapshot, engine_effective=event)
        elif isinstance(event, AlsaRuntimeEvidence):
            updated = replace(snapshot, device_negotiated=event)
        else:
            updated = replace(snapshot, anomalies=(*snapshot.anomalies, event))
        return classify_signal_truth(updated)

    def _publish(self) -> None:
        for callback in tuple(self._subscribers):
            with suppress(Exception):
                callback()
