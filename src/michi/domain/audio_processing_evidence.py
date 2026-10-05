"""DSP runtime evidence (AP2-F04, R11-F04 / §125).

Pure domain module: immutable, generation-scoped runtime facts. It records what
a backend actually did; it never commands execution and never assumes BYPASSED
from absent evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from michi.domain.audio_processing import ProcessingNodeKind
from michi.domain.audio_signal import PcmSignalFormat


class ProcessingActivity(StrEnum):
    NOT_PRESENT = "not_present"
    BYPASSED = "bypassed"
    PASS_THROUGH = "pass_through"
    ACTIVE = "active"
    UNKNOWN = "unknown"
    NOT_OBSERVABLE = "not_observable"


@dataclass(frozen=True, slots=True)
class ProcessingNodeRuntimeEvidence:
    graph_id: str
    graph_revision: int
    execution_generation: int
    node_id: str
    kind: ProcessingNodeKind
    activity: ProcessingActivity
    input_signal: PcmSignalFormat | None
    output_signal: PcmSignalFormat | None
    latency_samples: int | None
    backend_strategy: str | None
    observed_factories: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProcessingRuntimeSnapshot:
    graph_id: str
    graph_revision: int
    execution_generation: int
    backend_id: str
    input_signal: PcmSignalFormat | None
    output_signal: PcmSignalFormat | None
    nodes: tuple[ProcessingNodeRuntimeEvidence, ...]
    graph_bypassed: bool
    graph_inspection_complete: bool
    xruns: int
    measured_latency_frames: int | None
    peak_dbfs: float | None
    clipped_samples_observed: bool | None

    @property
    def active_nodes(self) -> tuple[ProcessingNodeRuntimeEvidence, ...]:
        return tuple(
            node for node in self.nodes if node.activity is ProcessingActivity.ACTIVE
        )

    @property
    def is_bypassed(self) -> bool:
        # Bypass is an explicit runtime fact. UNKNOWN, NOT_OBSERVABLE or an
        # empty evidence list never silently becomes BYPASSED.
        return self.graph_bypassed

    @property
    def has_observed_active_processing(self) -> bool:
        return bool(self.active_nodes)
