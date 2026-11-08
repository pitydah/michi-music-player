"""A24 PURE REFERENCE MODEL, NOT product code and NOT an authorized ABI.

Demonstrates the evidence necessary for associating effective F05 DSP with the
CURRENT OutputSession execution. It never controls playback, reads hardware,
imports Qt, adds a recorder, or asserts sample/physical fidelity.

IMPORTANT: RouteBindingProof, owner event sequences/epochs and certified
continuity are proposed producer contracts; they DO NOT exist in PR245's
ProcessingTruthEvent. Without them, product must yield UNCORRELATED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Correlation(StrEnum):
    CONFIRMED = "CONFIRMED"
    UNCORRELATED = "UNCORRELATED"
    STALE = "STALE"
    REVOKED = "REVOKED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class OutputScope:
    family: str
    execution_id: str | None
    session_generation: int | None
    state: str
    host_generation: int | None
    pipeline_generation: int | None
    binding_generation: int | None
    owner_revision: int | None


@dataclass(frozen=True, slots=True)
class DspOwner:
    state: str
    plan_id: str | None
    processing_generation: int | None
    runtime_identity: str | None
    readback_proven: bool
    host_generation: int | None
    pipeline_generation: int | None
    owner_revision: int | None
    event_epoch: int | None
    latest_event_sequence: int | None


@dataclass(frozen=True, slots=True)
class DspEvent:
    state: str
    plan_id: str | None
    processing_generation: int | None
    runtime_identity: str | None
    readback_proven: bool
    host_generation: int | None
    pipeline_generation: int | None
    event_epoch: int | None
    sequence: int | None


@dataclass(frozen=True, slots=True)
class RouteBindingProof:
    """PROPOSED owner-issued link; existing PR245 does not produce it.

    Names and numbers here are opaque comparisons, not cryptographic proof.
    Provenance is trusted only when created by the verified OutputSession owner.
    """

    issuing_owner: str
    adoption_state: str
    family: str
    execution_id: str
    session_generation: int
    output_owner_revision: int
    dsp_owner_revision: int
    host_generation: int
    pipeline_generation: int
    binding_generation: int
    dsp_plan_id: str
    dsp_generation: int
    dsp_runtime_identity: str


@dataclass(frozen=True, slots=True)
class ContinuityCertificate:
    """PROPOSED F05/recorder-verified stream epoch and complete ordered tail."""

    event_epoch: int
    latest_sequence: int
    ordered_tail_complete: bool
    owner_revision: int


@dataclass(frozen=True, slots=True)
class InputStability:
    recorder_revision_start: int
    recorder_revision_end: int
    output_revision_start: int
    output_revision_end: int
    dsp_revision_start: int
    dsp_revision_end: int


@dataclass(frozen=True, slots=True)
class Decision:
    correlation: Correlation
    blocker: str | None
    motor_readback_observed: bool
    confirmed_for_current_execution: bool


def _result(state: Correlation, blocker: str | None, owner: DspOwner) -> Decision:
    owner_proof = (
        owner.state == "effective"
        and owner.readback_proven is True
        and bool(owner.plan_id)
        and bool(owner.runtime_identity)
        and _positive(owner.processing_generation)
    )
    return Decision(state, blocker, owner_proof, state is Correlation.CONFIRMED)


def _positive(v: int | None) -> bool:
    return type(v) is int and v > 0


def correlate(
    output: OutputScope,
    owner: DspOwner,
    events: tuple[DspEvent, ...],
    *,
    link: RouteBindingProof | None,
    continuity: ContinuityCertificate | None,
    stable: InputStability | None,
) -> Decision:
    """Conservative ST-03 contract with explicit unknowns and revocation.

    This function models a future normalized source. The Qt bridge must NOT
    manufacture link/continuity objects from matching numeric generations.
    """
    if output.family not in ("managed", "dsd_pcm"):
        return _result(Correlation.UNCORRELATED, "ST03_FAMILY_NOT_DSP_SCOPED", owner)
    if output.state != "RUNNING" or not output.execution_id:
        return _result(
            Correlation.UNCORRELATED, "ST03_NOT_CURRENT_RUNNING_EXECUTION", owner
        )
    if not all(
        _positive(v)
        for v in (
            output.session_generation,
            output.host_generation,
            output.pipeline_generation,
            output.binding_generation,
            output.owner_revision,
        )
    ):
        return _result(Correlation.UNCORRELATED, "ST03_OUTPUT_FENCE_MISSING", owner)
    if stable is None or not (
        stable.recorder_revision_start == stable.recorder_revision_end
        and stable.output_revision_start
        == stable.output_revision_end
        == output.owner_revision
        and stable.dsp_revision_start == stable.dsp_revision_end == owner.owner_revision
    ):
        return _result(
            Correlation.UNCORRELATED, "ST03_CROSS_OWNER_READ_UNSTABLE", owner
        )
    if owner.state in ("bypassed", "unavailable"):
        return _result(Correlation.REVOKED, "ST03_DSP_OWNER_RETIRED", owner)
    if owner.state != "effective" or not owner.readback_proven:
        return _result(Correlation.UNCORRELATED, "ST03_OWNER_READBACK_UNPROVEN", owner)
    if not (
        owner.plan_id
        and owner.runtime_identity
        and all(
            _positive(v)
            for v in (
                owner.processing_generation,
                owner.host_generation,
                owner.pipeline_generation,
                owner.owner_revision,
                owner.event_epoch,
                owner.latest_event_sequence,
            )
        )
    ):
        return _result(Correlation.UNCORRELATED, "ST03_OWNER_FENCE_MISSING", owner)
    if (
        owner.host_generation != output.host_generation
        or owner.pipeline_generation != output.pipeline_generation
    ):
        return _result(Correlation.CONFLICTED, "ST03_HOST_OR_PIPELINE_CONFLICT", owner)

    # This link is an external positive assertion by the existing OUTPUT owner.
    # Mere equality of host/pipeline integers cannot create it.
    if link is None:
        return _result(Correlation.UNCORRELATED, "ST03_EXECUTION_LINK_MISSING", owner)
    if link.issuing_owner != "OUTPUT_SESSION" or link.adoption_state != "ADOPTED":
        return _result(Correlation.UNCORRELATED, "ST03_EXECUTION_LINK_UNTRUSTED", owner)
    if not (
        link.family == output.family
        and link.execution_id == output.execution_id
        and link.session_generation == output.session_generation
        and link.output_owner_revision == output.owner_revision
        and link.dsp_owner_revision == owner.owner_revision
        and link.host_generation == output.host_generation
        and link.pipeline_generation == output.pipeline_generation
        and link.binding_generation == output.binding_generation
        and link.dsp_plan_id == owner.plan_id
        and link.dsp_generation == owner.processing_generation
        and link.dsp_runtime_identity == owner.runtime_identity
    ):
        return _result(Correlation.CONFLICTED, "ST03_EXECUTION_LINK_CONFLICT", owner)

    if continuity is None or (
        continuity.event_epoch != owner.event_epoch
        or continuity.latest_sequence != owner.latest_event_sequence
        or continuity.owner_revision != owner.owner_revision
        or not continuity.ordered_tail_complete
    ):
        return _result(
            Correlation.UNCORRELATED, "ST03_CAUSAL_CONTINUITY_UNPROVEN", owner
        )
    if not events:
        return _result(Correlation.UNCORRELATED, "ST03_EVENT_ABSENT", owner)
    if any(
        (event.event_epoch != owner.event_epoch or not _positive(event.sequence))
        for event in events
    ):
        return _result(Correlation.UNCORRELATED, "ST03_EVENT_SCOPE_UNVERIFIED", owner)
    seqs = tuple(event.sequence for event in events)
    if len(set(seqs)) != len(seqs) or seqs != tuple(sorted(seqs)):
        return _result(Correlation.CONFLICTED, "ST03_SEQUENCE_ORDER_INVALID", owner)
    if seqs[-1] != continuity.latest_sequence:
        return _result(
            Correlation.UNCORRELATED, "ST03_LATEST_EVENT_NOT_CAPTURED", owner
        )
    # Detect gaps even in a truncated tail; owner-certified completeness is
    # necessary, never inferred from a consecutive-looking local array.
    if any(right != left + 1 for left, right in zip(seqs, seqs[1:], strict=False)):
        return _result(Correlation.UNCORRELATED, "ST03_EVENT_SEQUENCE_GAP", owner)

    latest = events[-1]
    if latest.state in ("BYPASSED", "UNAVAILABLE", "RELEASED", "UNKNOWN"):
        return _result(Correlation.REVOKED, "ST03_LATEST_EVENT_TERMINAL", owner)
    if latest.state != "EFFECTIVE":
        return _result(
            Correlation.UNCORRELATED, "ST03_LATEST_EVENT_NOT_EFFECTIVE", owner
        )
    if not latest.readback_proven:
        return _result(Correlation.UNCORRELATED, "ST03_LATEST_EVENT_NO_READBACK", owner)
    if (
        latest.plan_id != owner.plan_id
        or latest.processing_generation != owner.processing_generation
        or latest.runtime_identity != owner.runtime_identity
        or latest.host_generation != owner.host_generation
        or latest.pipeline_generation != owner.pipeline_generation
    ):
        return _result(Correlation.STALE, "ST03_LATEST_EVENT_MISMATCH", owner)
    return _result(Correlation.CONFIRMED, None, owner)
