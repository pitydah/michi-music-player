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
    #: R110R1 final fail-closed seal: a KNOWN unequal significant-bit value.
    ST_SIGNIFICANT_BITS_MISMATCH = "ST_SIGNIFICANT_BITS_MISMATCH"
    #: The representation changed but no mechanism responsible for it was
    #: observed (converter absent, or the observed converter claims passthrough).
    ST_CONTAINER_TRANSFORM_UNOBSERVED = "ST_CONTAINER_TRANSFORM_UNOBSERVED"


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


def _authorized_preservation_decision(
    *,
    requested: PcmTuple,
    decoded: PcmTuple,
    effective: PcmTuple,
    alsa: PcmTuple,
    transforms: RuntimeTransformEvidence,
) -> tuple[SignalTruthVerdict, SignalTruthReason] | None:
    """Decide an AUTHORIZED representation-preserving widening route (R110R1).

    Canonical §292/§297: an explicitly configured representation-only
    transformation is auditable evidence, so a proven authorized route is
    classified BEFORE the epistemic container-bit guard — the CARRIER is a
    container, its width is not the signal's precision.

    Returns ``None`` for every other route so the established classification
    keeps governing unchanged:

    * identical representation            -> existing DIRECT path
    * unauthorized / unrequested rewrite  -> existing DSP path
    * rate / channel / negotiation clash  -> existing CONTRADICTED path
    """
    norm = lambda pcm: pcm.transport_format.replace("_", "").upper()  # noqa: E731

    decoded_format = norm(decoded)
    requested_format = norm(requested)
    effective_format = norm(effective)
    alsa_format = norm(alsa)

    if decoded_format == effective_format == alsa_format:
        return None
    bits = decoded.significant_bits
    if bits is None:
        return None
    # The carrier POLICY selects the authorized pair for the width the plan
    # DECLARED; a known discrepancy between that declared width and the proven
    # signal is then a contradiction (R110 §21/§22) rather than an epistemic
    # unknown. Pairs that are not authorized for any width keep the established
    # classification untouched (a real rewrite stays DSP).
    requested_bits = requested.significant_bits
    authorized = _ALLOWED_CONTAINER_ADAPTATIONS.get(
        bits, frozenset()
    ) | _ALLOWED_CONTAINER_ADAPTATIONS.get(requested_bits, frozenset())
    if (decoded_format, requested_format) not in authorized:
        return None
    if requested_bits is not None and requested_bits != bits:
        return (
            SignalTruthVerdict.CONTRADICTED,
            SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH,
        )
    if not (effective_format == alsa_format == requested_format):
        return None
    # Rate and channel clashes are contradictions, not preservation questions.
    if not (decoded.rate_hz == requested.rate_hz == effective.rate_hz == alsa.rate_hz):
        return None
    if not (
        decoded.channels == requested.channels == effective.channels == alsa.channels
    ):
        return None
    # A PROVEN carrier width that contradicts the decoded signal is a known
    # mismatch, never an epistemic unknown (§21).
    for known in (effective.significant_bits, alsa.significant_bits):
        if known is not None and known != bits:
            return (
                SignalTruthVerdict.CONTRADICTED,
                SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH,
            )
    if requested.significant_bits != bits:
        return (
            SignalTruthVerdict.CONTRADICTED,
            SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH,
        )
    if transforms.resampler_present and transforms.resampler_transforming is not False:
        return (
            SignalTruthVerdict.UNKNOWN,
            SignalTruthReason.ST_RESAMPLER_STATE_UNKNOWN,
        )
    # §12 required positive chain: the representation changed, so preservation
    # can only be claimed through an OBSERVED mechanism that proves it.
    if not transforms.converter_present:
        # AUTHORIZED is not OBSERVED: no mechanism responsible for the change
        # was observed.
        return (
            SignalTruthVerdict.UNKNOWN,
            SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED,
        )
    if transforms.remix_transforming is not False:
        return (
            SignalTruthVerdict.UNKNOWN,
            SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN,
        )
    if transforms.converter_transforming is None:
        return (
            SignalTruthVerdict.UNKNOWN,
            SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN,
        )
    if transforms.converter_transforming is False:
        # Contradictory evidence: the endpoint proves the representation changed
        # while the observed converter claims it did NOT transform, so the
        # responsible mechanism is unobserved. Fail closed.
        return (
            SignalTruthVerdict.CONTRADICTED,
            SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED,
        )
    if (
        transforms.converter_dithering_disabled is None
        or transforms.converter_noise_shaping_disabled is None
    ):
        # A transforming converter whose preservation configuration cannot be
        # proven is never assumed harmless.
        return (
            SignalTruthVerdict.UNKNOWN,
            SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN,
        )
    if not (
        transforms.converter_dithering_disabled
        and transforms.converter_noise_shaping_disabled
    ):
        return (
            SignalTruthVerdict.DSP,
            SignalTruthReason.ST_DSP_PRESENT,
        )
    return (
        SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED,
        SignalTruthReason.ST_CONTAINER_ADAPTED,
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


def signal_truth_snapshot_diagnostics(snapshot) -> dict:
    """Read-only normalized view of ONE Signal Truth candidate (R110 §12/§13).

    The field harness is an OBSERVER: this serializer is the single authority
    that decides how Signal Truth facts are exposed, so no second classifier or
    parallel truth model can drift from the recorder. Only normalized values are
    returned — never a Gst object or a QObject.
    """

    def pcm(item):
        if item is None:
            return None
        return {
            "format": item.transport_format,
            "rate_hz": item.rate_hz,
            "channels": item.channels,
            "significant_bits": item.significant_bits,
        }

    decoded = snapshot.decoded_runtime
    engine = snapshot.engine_effective
    alsa = snapshot.device_negotiated
    plan = snapshot.plan
    transforms = engine.transform_evidence if engine is not None else None
    identity = snapshot.identity
    return {
        "identity": {
            "plan_id": identity.plan_id,
            "execution_generation": identity.execution_generation,
            "port_generation": identity.port_generation,
            "binding_generation": identity.binding_generation,
            "stable_device_id": identity.stable_device_id,
            "stable_endpoint_signature": identity.stable_endpoint_signature,
        },
        "plan": {
            "requested": pcm(plan.requested_pcm),
            "sink_factory": plan.sink_factory,
            "sink_device": plan.sink_device,
            "fixed_gain_required": plan.fixed_gain_required,
        },
        "decoded": pcm(decoded.pcm) if decoded is not None else None,
        "engine": {
            **(pcm(engine.effective_pcm) if engine is not None else {}),
            "graph_inspection_complete": (
                engine.graph_inspection_complete if engine is not None else None
            ),
            "graph_factories": (
                list(engine.graph_factories) if engine is not None else []
            ),
            "software_gain": engine.software_gain if engine is not None else None,
            "muted": engine.muted if engine is not None else None,
        },
        "transform": (
            {
                "converter_present": transforms.converter_present,
                "converter_transforming": transforms.converter_transforming,
                "converter_dithering_disabled": (
                    transforms.converter_dithering_disabled
                ),
                "converter_noise_shaping_disabled": (
                    transforms.converter_noise_shaping_disabled
                ),
                "resampler_present": transforms.resampler_present,
                "resampler_transforming": transforms.resampler_transforming,
                "remix_transforming": transforms.remix_transforming,
            }
            if transforms is not None
            else None
        ),
        "alsa": pcm(alsa.negotiated_pcm) if alsa is not None else None,
        "clock": {
            "sink_provides_clock": (
                engine.sink_provides_clock if engine is not None else None
            ),
            "sink_clock_is_pipeline_clock": (
                engine.sink_clock_is_pipeline_clock if engine is not None else None
            ),
            "slave_method": engine.slave_method if engine is not None else None,
        },
        "verdict": {
            "state": snapshot.verdict.value,
            "reason_codes": [reason.value for reason in snapshot.reasons],
        },
    }


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


#: Explicitly authorized container-WIDTH adaptations per proven signal width,
#: as ordered ``(decoded, requested)`` pairs. A pair transports the same
#: significant value exactly (the narrower samples are left-shifted into the
#: wider container with zero fill). Membership in a format family is NOT
#: enough: an arbitrary or narrowing rewrite must never be reported as an
#: adaptation (R1.3.1 §32/§33).
_ALLOWED_CONTAINER_ADAPTATIONS: dict[int, frozenset[tuple[str, str]]] = {
    16: frozenset({("S16LE", "S32LE")}),
    24: frozenset(
        {
            # Packed 3-byte 24 (GStreamer S24_3LE).
            ("S243LE", "S2432LE"),
            ("S243LE", "S32LE"),
            # 24-bit-in-32 storage (GStreamer S24LE / S24_32LE). The physical
            # decoder for a 24-bit PCM source reports S24LE, so omitting these
            # pairs silently dropped the 24-bit route to UNKNOWN.
            ("S24LE", "S2432LE"),
            ("S24LE", "S32LE"),
            ("S2432LE", "S32LE"),
        }
    ),
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
    allowed_pairs = _ALLOWED_CONTAINER_ADAPTATIONS.get(bits)
    if allowed_pairs is None:
        return False
    requested_format = requested_pcm.transport_format.replace("_", "").upper()
    decoded_format = decoded_pcm.transport_format.replace("_", "").upper()
    if (decoded_format, requested_format) not in allowed_pairs:
        # Not an explicitly authorized widening pair: never an adaptation.
        return False
    if requested_pcm.significant_bits != bits:
        return False
    if requested_pcm.rate_hz != decoded_pcm.rate_hz:
        return False
    if requested_pcm.channels != decoded_pcm.channels:
        return False
    # The negotiated set may contain exactly the two authorized formats.
    return negotiated_formats <= {decoded_format, requested_format}


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
    if decoded is not None and decoded.pcm.significant_bits is None:
        # R110R1 TRAP 3: only the DECODED signal width is an epistemic fact the
        # classifier cannot do without. The engine/ALSA stages report a
        # CARRIER container whose intrinsic width is legitimately unknown for
        # S32_LE; an authorized representation-preserving route is decided by
        # _authorized_preservation_decision() below, and every other route
        # still fails closed through the equality check that follows.
        missing.add(SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN)
    if missing:
        return result(SignalTruthVerdict.UNKNOWN, _ordered(missing, _UNKNOWN_ORDER))

    assert decoded is not None and engine is not None and alsa is not None
    assert engine.effective_pcm is not None
    signals = (decoded.pcm, engine.effective_pcm, alsa.negotiated_pcm)
    # R110R1: a PROVEN authorized representation-preserving widening is decided
    # before the epistemic container-bit guard. Every other route returns None
    # and keeps the established classification.
    preservation_decision = _authorized_preservation_decision(
        requested=plan.requested_pcm,
        decoded=decoded.pcm,
        effective=engine.effective_pcm,
        alsa=alsa.negotiated_pcm,
        transforms=engine.transform_evidence,
    )
    if preservation_decision is not None:
        verdict, reason = preservation_decision
        return result(verdict, (reason,))
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
