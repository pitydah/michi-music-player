"""AP2-F06 — Managed PCM output contract (specific DAC, processed path).

MANAGED_PCM is a Michi-owned *output family*, never a fourth audio engine
and never a Direct variant with different booleans. The plan is immutable and
self-sufficient: it names the exact selected binding, the compiled processing
identity, the demonstrated terminal format and the explicit transformation
policy. The executor consults no profile/policy service.

Contract anchors: R11-F06, R11-G02 (authority map), R11-G03 (output families)
and R11-G04 (processing sample contract).
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.domain.audio_evidence import PcmTuple

#: Stable path tag. Never ``direct``/``hardware_raw``.
MANAGED_PCM_PATH = "managed_pcm"


class ManagedPcmPlanError(ValueError):
    """Invalid plan construction (a planner bug, never a runtime policy)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ManagedPcmOutputPlan:
    """One specific-DAC processed execution plan.

    ``terminal_format`` is a GStreamer raw format (for example ``S32LE``)
    proven by current native evidence; ``source_pcm`` is the decoded source
    tuple BEFORE processing. ``transform_policy`` lists, explicitly, every
    transformation the execution performs (dsp, representation conversion,
    rate change, channel map, quantization). Nothing is implied.
    """

    plan_id: str
    stable_device_id: str
    device_locator: str
    binding_generation: int

    source_pcm: PcmTuple
    processing_plan_id: str | None
    processing_graph_revision: int
    processing_revision: int
    working_format: str

    output_rate_hz: int
    output_channels: int
    terminal_format: str

    volume_policy: str
    selection_revision: int
    execution_id: str
    transform_policy: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    path: str = MANAGED_PCM_PATH

    def __post_init__(self) -> None:
        if self.path != MANAGED_PCM_PATH:
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_PATH_INVALID", f"path {self.path!r} is not managed"
            )
        if not self.plan_id.strip():
            raise ManagedPcmPlanError("MANAGED_PLAN_ID_MISSING", "plan_id is empty")
        if not self.stable_device_id.strip():
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_DEVICE_MISSING", "stable device id is empty"
            )
        if not self.device_locator.strip():
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_BINDING_MISSING", "device locator is empty"
            )
        if self.binding_generation < 0:
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_GENERATION_INVALID", "binding generation < 0"
            )
        if self.output_rate_hz <= 0 or self.output_channels <= 0:
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_PCM_INVALID", "invalid output rate/channels"
            )
        if not self.terminal_format.strip():
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_TERMINAL_MISSING", "terminal format is empty"
            )
        if not self.execution_id.strip():
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_EXECUTION_MISSING", "execution id is empty"
            )
        if not self.transform_policy:
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_TF_POLICY_MISSING",
                "transform policy must be explicit (possibly 'identity')",
            )
        if not self.volume_policy.strip():
            raise ManagedPcmPlanError(
                "MANAGED_PLAN_VOLUME_POLICY_MISSING", "volume policy is empty"
            )


@dataclass(frozen=True, slots=True)
class ManagedPcmRefusal:
    """Typed planning refusal: the selected device/intent is preserved."""

    code: str
    detail: str
    decisions: tuple[str, ...] = ()
