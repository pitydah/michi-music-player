"""Signal Path projection service (AP2-F03, R11-F03).

Pure, deterministic projection of ONE classified ``SignalTruthSnapshot`` into
the family-neutral path read model. It never commands runtime, never touches
hardware and never creates a second truth: ``SignalTruthRecorder`` classifies,
``SignalPathService`` explains, and M11.5 owns proof semantics.

Reason ownership is explicit and total: every ``SignalTruthReason`` has exactly
one primary node in ``PRIMARY_NODE_BY_REASON`` so no reason can be dropped and
none can be duplicated across nodes. Snapshot-level verdict/reasons are carried
1:1; per-node codes preserve the classifier's order.
"""

from __future__ import annotations

from typing import ClassVar

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_path import (
    SignalPathEdge,
    SignalPathIdentity,
    SignalPathNode,
    SignalPathNodeKind,
    SignalPathNodeState,
    SignalPathProjectionError,
    SignalPathSnapshot,
)
from michi.domain.signal_truth import (
    SignalTruthReason,
    SignalTruthSnapshot,
)

_CONTRADICTION_REASONS = frozenset(
    {
        SignalTruthReason.ST_DEVICE_MISMATCH,
        SignalTruthReason.ST_BINDING_MISMATCH,
        SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION,
        SignalTruthReason.ST_SINK_MISMATCH,
        SignalTruthReason.ST_RUNTIME_ERROR,
        SignalTruthReason.ST_XRUN,
        SignalTruthReason.ST_GAIN_NOT_UNITY,
        SignalTruthReason.ST_CLOCK_POLICY_MISMATCH,
    }
)

#: Reasons that only appear when the classified verdict is CONTRADICTED.
_CONFLICTING_REASONS = _CONTRADICTION_REASONS | {
    SignalTruthReason.ST_RATE_MISMATCH,
    SignalTruthReason.ST_CHANNEL_MISMATCH,
    SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH,
    SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED,
}

_NODE_LABELS: dict[SignalPathNodeKind, str] = {
    SignalPathNodeKind.SOURCE: "Source",
    SignalPathNodeKind.DECODE: "Decode",
    SignalPathNodeKind.ENGINE: "Engine",
    SignalPathNodeKind.DEVICE: "Device",
}


def _facts(**pairs: object) -> tuple[tuple[str, object], ...]:
    """Canonical fact tuple: sorted by key, scalars only, insertion-order free."""
    return tuple(sorted(pairs.items()))


def _pcm_facts(pcm: PcmTuple) -> tuple[tuple[str, object], ...]:
    return _facts(
        format=pcm.transport_format,
        rate_hz=pcm.rate_hz,
        channels=pcm.channels,
        significant_bits=pcm.significant_bits,
    )


class SignalPathService:
    """Read-only projection from classified Signal Truth to the path read model."""

    #: Total reason -> primary node table (see module docstring).
    PRIMARY_NODE_BY_REASON: ClassVar[dict[SignalTruthReason, SignalPathNodeKind]] = {
        # Contradiction family.
        SignalTruthReason.ST_DEVICE_MISMATCH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_BINDING_MISMATCH: SignalPathNodeKind.DEVICE,
        SignalTruthReason.ST_SINK_MISMATCH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_RUNTIME_ERROR: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_XRUN: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_GAIN_NOT_UNITY: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_CLOCK_POLICY_MISMATCH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION: SignalPathNodeKind.DEVICE,
        # Transform family.
        SignalTruthReason.ST_RESAMPLER_PRESENT: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_RATE_MISMATCH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_REMIX_OBSERVED: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_CHANNEL_MISMATCH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_DSP_PRESENT: SignalPathNodeKind.ENGINE,
        # Container / carrier facts.
        SignalTruthReason.ST_CONTAINER_ADAPTED: SignalPathNodeKind.DEVICE,
        SignalTruthReason.ST_SIGNIFICANT_BITS_MISMATCH: SignalPathNodeKind.DEVICE,
        SignalTruthReason.ST_CONTAINER_TRANSFORM_UNOBSERVED: SignalPathNodeKind.ENGINE,
        # Missing / unknown epistemic family.
        SignalTruthReason.ST_MISSING_DECODED: SignalPathNodeKind.DECODE,
        SignalTruthReason.ST_MISSING_ENGINE_EFFECTIVE: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_MISSING_ALSA: SignalPathNodeKind.DEVICE,
        SignalTruthReason.ST_MISSING_GRAPH: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_MISSING_GAIN: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_MISSING_CLOCK: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN: SignalPathNodeKind.DECODE,
        SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_RESAMPLER_STATE_UNKNOWN: SignalPathNodeKind.ENGINE,
        SignalTruthReason.ST_SOURCE_DECODED_MISMATCH: SignalPathNodeKind.SOURCE,
    }

    def project(self, snapshot: SignalTruthSnapshot) -> SignalPathSnapshot:
        """Explain one classified snapshot; refuse any foreign generation."""
        identity = snapshot.identity
        self._refuse_foreign_identity(snapshot, identity)
        plan = snapshot.plan
        plan_facts = _pcm_facts(plan.requested_pcm)
        base_ref = f"signal-truth:{identity.plan_id}:{identity.execution_generation}"
        nodes = (
            self._node(
                snapshot,
                SignalPathNodeKind.SOURCE,
                requested=(),
                effective=self._source_facts(snapshot),
                observed=snapshot.source_file_facts is not None,
                base_ref=base_ref,
            ),
            self._node(
                snapshot,
                SignalPathNodeKind.DECODE,
                requested=(),
                effective=(
                    _pcm_facts(snapshot.decoded_runtime.pcm)
                    if snapshot.decoded_runtime is not None
                    else ()
                ),
                observed=snapshot.decoded_runtime is not None,
                base_ref=base_ref,
            ),
            self._node(
                snapshot,
                SignalPathNodeKind.ENGINE,
                requested=plan_facts,
                effective=self._engine_facts(snapshot),
                observed=(
                    snapshot.engine_effective is not None
                    and snapshot.engine_effective.effective_pcm is not None
                ),
                base_ref=base_ref,
            ),
            self._node(
                snapshot,
                SignalPathNodeKind.DEVICE,
                requested=plan_facts,
                effective=self._device_facts(snapshot),
                observed=snapshot.device_negotiated is not None,
                base_ref=base_ref,
            ),
        )
        kind_order = [node.kind for node in nodes]
        edges = tuple(
            SignalPathEdge(
                source_node_id=str(kind_order[index]),
                target_node_id=str(kind_order[index + 1]),
            )
            for index in range(len(kind_order) - 1)
        )
        return SignalPathSnapshot(
            identity=SignalPathIdentity(
                plan_id=identity.plan_id,
                execution_generation=identity.execution_generation,
                port_generation=identity.port_generation,
                binding_generation=identity.binding_generation,
                stable_device_id=identity.stable_device_id,
                stable_endpoint_signature=identity.stable_endpoint_signature,
            ),
            nodes=nodes,
            edges=edges,
            verdict=snapshot.verdict.value,
            reasons=tuple(reason.value for reason in snapshot.reasons),
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _refuse_foreign_identity(self, snapshot: SignalTruthSnapshot, identity) -> None:
        pieces = [snapshot.plan.identity]
        for piece in (
            snapshot.source_file_facts,
            snapshot.decoded_runtime,
            snapshot.engine_effective,
            snapshot.device_negotiated,
        ):
            if piece is not None:
                pieces.append(piece.identity)
        pieces.extend(anomaly.identity for anomaly in snapshot.anomalies)
        for piece in pieces:
            if piece != identity:
                raise SignalPathProjectionError(
                    "signal path refuses to merge evidence from a different identity"
                )

    def _node(
        self,
        snapshot: SignalTruthSnapshot,
        kind: SignalPathNodeKind,
        *,
        requested: tuple[tuple[str, object], ...],
        effective: tuple[tuple[str, object], ...],
        observed: bool,
        base_ref: str,
    ) -> SignalPathNode:
        own_reasons = tuple(
            reason.value
            for reason in snapshot.reasons
            if self.PRIMARY_NODE_BY_REASON[reason] is kind
        )
        conflicted = snapshot.verdict.value == "contradicted" and any(
            reason in _CONFLICTING_REASONS
            for reason in snapshot.reasons
            if self.PRIMARY_NODE_BY_REASON[reason] is kind
        )
        if conflicted:
            state = SignalPathNodeState.CONFLICTED
        elif observed:
            state = SignalPathNodeState.OBSERVED
        elif (
            kind is SignalPathNodeKind.ENGINE and snapshot.engine_effective is not None
        ):
            # The engine stage exists but its effective signal was never observed.
            state = SignalPathNodeState.UNKNOWN
        else:
            state = SignalPathNodeState.NOT_OBSERVED
        refs = [f"{base_ref}#{kind.value}"]
        if kind is SignalPathNodeKind.ENGINE:
            for anomaly in snapshot.anomalies:
                ref = f"{base_ref}#anomaly:{anomaly.kind.value}"
                if ref not in refs:
                    refs.append(ref)
        return SignalPathNode(
            node_id=kind.value,
            kind=kind,
            label=_NODE_LABELS[kind],
            state=state,
            requested=requested,
            effective=effective,
            reason_codes=own_reasons,
            evidence_refs=tuple(refs),
        )

    def _source_facts(
        self, snapshot: SignalTruthSnapshot
    ) -> tuple[tuple[str, object], ...]:
        source = snapshot.source_file_facts
        if source is None:
            return ()
        facts: dict[str, object] = {
            "container": source.container,
            "codec": source.codec,
        }
        if source.nominal_pcm is not None:
            facts.update(
                {
                    f"nominal_{key}": value
                    for key, value in _pcm_facts(source.nominal_pcm)
                }
            )
        return _facts(**facts)

    def _engine_facts(
        self, snapshot: SignalTruthSnapshot
    ) -> tuple[tuple[str, object], ...]:
        engine = snapshot.engine_effective
        if engine is None:
            return ()
        facts: dict[str, object] = {
            "sink_factory": engine.sink_factory,
            "sink_device": engine.sink_device,
            "graph_inspection_complete": engine.graph_inspection_complete,
            "graph_factories": ",".join(engine.graph_factories),
            "software_gain": engine.software_gain,
            "muted": engine.muted,
            "resampling_observed": engine.resampling_observed,
            "remix_observed": engine.remix_observed,
            "dsp_observed": engine.dsp_observed,
        }
        if engine.effective_pcm is not None:
            facts.update(_pcm_facts(engine.effective_pcm))
        return _facts(**facts)

    def _device_facts(
        self, snapshot: SignalTruthSnapshot
    ) -> tuple[tuple[str, object], ...]:
        alsa = snapshot.device_negotiated
        if alsa is None:
            return ()
        facts: dict[str, object] = {
            "binding_matches": alsa.binding_matches,
            "access": alsa.access,
            "subformat": alsa.subformat,
        }
        if alsa.locator is not None:
            facts["locator"] = alsa.locator
        facts.update(_pcm_facts(alsa.negotiated_pcm))
        return _facts(**facts)
