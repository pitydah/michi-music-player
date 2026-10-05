"""Family-neutral signal path projection domain (AP2-F03, R11-F03).

Pure domain module: stdlib only, no I/O and no execution authority. The signal
path EXPLAINS classified Signal Truth snapshots; it never creates truth,
commands playback or performs device access. ``SignalTruthRecorder`` remains
the single runtime truth authority and M11.5 owns proof/conformance semantics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

_FACT_SCALAR_TYPES = (str, int, float, bool, type(None))


class SignalPathNodeKind(StrEnum):
    """Canonical stages of the projected path (Direct parity: four stages)."""

    SOURCE = "source"
    DECODE = "decode"
    ENGINE = "engine"
    DEVICE = "device"


class SignalPathNodeState(StrEnum):
    """Observability of one stage (spec 127 vocabulary, never proof)."""

    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    NOT_OBSERVABLE = "not_observable"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONFLICTED = "conflicted"


class SignalPathProjectionError(ValueError):
    """Typed refusal: evidence from different generations never merges."""


def _validate_facts(facts: tuple[tuple[str, object], ...], field: str) -> None:
    seen: set[str] = set()
    for pair in facts:
        if not (isinstance(pair, tuple) and len(pair) == 2):
            raise ValueError(f"{field} facts must be (key, value) pairs")
        key, value = pair
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{field} fact keys must be non-empty strings")
        if key in seen:
            raise ValueError(f"{field} fact keys must be unique")
        seen.add(key)
        if not isinstance(value, _FACT_SCALAR_TYPES):
            raise TypeError(
                f"{field} fact {key!r} must be a scalar value, never a runtime object"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{field} fact {key!r} must be finite")


@dataclass(frozen=True, slots=True)
class SignalPathNode:
    """One immutable, deterministic, serializable path stage."""

    node_id: str
    kind: SignalPathNodeKind
    label: str
    state: SignalPathNodeState
    requested: tuple[tuple[str, object], ...]
    effective: tuple[tuple[str, object], ...]
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("signal path node requires a node_id")
        if not self.label.strip():
            raise ValueError("signal path node requires a label")
        _validate_facts(self.requested, "requested")
        _validate_facts(self.effective, "effective")

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "kind": str(self.kind),
            "label": self.label,
            "state": str(self.state),
            "requested": {key: value for key, value in self.requested},
            "effective": {key: value for key, value in self.effective},
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class SignalPathEdge:
    source_node_id: str
    target_node_id: str


@dataclass(frozen=True, slots=True)
class SignalPathIdentity:
    """Mirror of the Signal Truth identity: the generation-safety anchor."""

    plan_id: str
    execution_generation: int
    port_generation: int
    binding_generation: int
    stable_device_id: str
    stable_endpoint_signature: str | None


@dataclass(frozen=True, slots=True)
class SignalPathSnapshot:
    """Deterministic read model over ONE classified Signal Truth snapshot."""

    identity: SignalPathIdentity
    nodes: tuple[SignalPathNode, ...]
    edges: tuple[SignalPathEdge, ...]
    verdict: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        ids = {node.node_id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("signal path node ids must be unique")
        for edge in self.edges:
            if edge.source_node_id not in ids or edge.target_node_id not in ids:
                raise ValueError("signal path edge references an unknown node")

    def node(self, node_id: str) -> SignalPathNode | None:
        return next((node for node in self.nodes if node.node_id == node_id), None)

    def to_dict(self) -> dict:
        return {
            "identity": {
                "plan_id": self.identity.plan_id,
                "execution_generation": self.identity.execution_generation,
                "port_generation": self.identity.port_generation,
                "binding_generation": self.identity.binding_generation,
                "stable_device_id": self.identity.stable_device_id,
                "stable_endpoint_signature": self.identity.stable_endpoint_signature,
            },
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [
                {"source": edge.source_node_id, "target": edge.target_node_id}
                for edge in self.edges
            ],
        }
