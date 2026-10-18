"""AP2-F06 — pure Managed PCM planner (specific DAC, processed route).

The planner decides; executors obey. It never consults profile/policy
services and never falls back: an unproven device, binding, selection
revision or terminal format is a TYPED refusal that preserves the user's
selected intent.

Initial policy (R11-F06):
* output rate = source rate unless the compiled plan contains a ResampleNode;
* output channels = source channels unless the plan contains a ChannelMapNode;
* the terminal container comes ONLY from proven current capability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from michi.application.processing_graph_compiler import CompiledProcessingPlan
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_output import VolumePolicy
from michi.domain.managed_pcm_output import (
    MANAGED_PCM_PATH,
    ManagedPcmOutputPlan,
    ManagedPcmRefusal,
)

_ALSA_PCM = "alsa_pcm"
_VALID_VOLUME_POLICIES = frozenset(policy.value for policy in VolumePolicy)
#: Deterministic ordered preference for an identity (no DSP) managed route.
_PREFERRED_TERMINALS = ("S32LE", "S24LE", "S16LE")


@dataclass(frozen=True, slots=True)
class ManagedPcmPlannerFacts:
    """Everything the planner may use. No hidden service lookups."""

    selected_device_id: str | None
    binding: object | None
    binding_device_id: str | None
    source_pcm: PcmTuple
    compiled_plan: CompiledProcessingPlan | None
    #: Raw GStreamer terminal formats PROVEN by current native evidence.
    terminal_formats: frozenset[str]
    volume_policy: str
    selection_revision: int
    current_selection_revision: int


class ManagedPcmOutputPlanner:
    """Deterministic planner: same facts => same plan (same execution id)."""

    def plan(
        self, facts: ManagedPcmPlannerFacts
    ) -> ManagedPcmOutputPlan | ManagedPcmRefusal:
        decisions: list[str] = []

        if not facts.selected_device_id:
            return ManagedPcmRefusal(
                "SELECTED_DEVICE_MISSING", "no Managed device is selected"
            )
        if (
            facts.binding_device_id is not None
            and facts.binding_device_id != facts.selected_device_id
        ):
            return ManagedPcmRefusal(
                "BINDING_SELECTION_MISMATCH",
                "ALSA binding does not belong to the selected device",
                tuple(decisions),
            )
        binding = facts.binding
        if binding is None:
            return ManagedPcmRefusal(
                "BINDING_UNAVAILABLE",
                "no current ALSA playback binding for the selected device",
                tuple(decisions),
            )
        kind = getattr(binding, "kind", None)
        kind_value = getattr(kind, "value", kind)
        if kind_value != _ALSA_PCM:
            return ManagedPcmRefusal(
                "BINDING_NOT_ALSA",
                f"binding kind {kind_value!r} is not a specific ALSA PCM",
                tuple(decisions),
            )
        locator = str(getattr(binding, "locator", "") or "").strip()
        if not locator:
            return ManagedPcmRefusal(
                "BINDING_UNAVAILABLE", "ALSA binding has no locator", tuple(decisions)
            )
        if not bool(getattr(binding, "currently_available", False)):
            return ManagedPcmRefusal(
                "DEVICE_UNAVAILABLE",
                "the selected binding is not currently available",
                tuple(decisions),
            )
        if facts.current_selection_revision != facts.selection_revision:
            return ManagedPcmRefusal(
                "SELECTION_STALE",
                "the selection revision was superseded while planning",
                tuple(decisions),
            )
        if facts.volume_policy not in _VALID_VOLUME_POLICIES:
            return ManagedPcmRefusal(
                "VOLUME_POLICY_INVALID",
                f"volume policy {facts.volume_policy!r} is not explicit",
                tuple(decisions),
            )
        decisions.append("selected_binding_alsa")

        plan = facts.compiled_plan
        source = facts.source_pcm
        if plan is not None:
            contract = plan.sample_contract
            if (
                contract.input_rate_hz != source.rate_hz
                or contract.channels_in != source.channels
            ):
                return ManagedPcmRefusal(
                    "PROCESSING_PLAN_MISMATCH",
                    "compiled plan was built for a different source tuple",
                    tuple(decisions),
                )
            output_rate = contract.output_rate_hz
            output_channels = contract.channels_out
            if output_rate != source.rate_hz and not plan.changes_rate:
                return ManagedPcmRefusal(
                    "RATE_POLICY_VIOLATION",
                    "rate changed without an explicit ResampleNode",
                    tuple(decisions),
                )
            if output_channels != source.channels and not plan.changes_channels:
                return ManagedPcmRefusal(
                    "CHANNEL_POLICY_VIOLATION",
                    "channels changed without an explicit ChannelMapNode",
                    tuple(decisions),
                )
            terminal_format = contract.output_format
            transform_policy = _transform_policy(plan)
            processing_plan_id = plan.plan_id
            graph_revision = plan.graph_revision
            working_format = contract.working_format
        else:
            output_rate = source.rate_hz
            output_channels = source.channels
            terminal_format = _preferred_terminal(facts.terminal_formats)
            transform_policy = ("identity",)
            processing_plan_id = None
            graph_revision = 0
            working_format = source.transport_format

        proven = {str(value).strip() for value in facts.terminal_formats}
        if str(terminal_format) not in proven:
            return ManagedPcmRefusal(
                "TERMINAL_FORMAT_UNPROVEN",
                f"terminal format {terminal_format!r} has no proven capability",
                tuple(decisions),
            )
        decisions.append("terminal_proven")

        execution_id = _execution_id(
            plan_id=processing_plan_id,
            device_id=facts.selected_device_id,
            locator=locator,
            binding_generation=int(getattr(binding, "generation", 0) or 0),
            selection_revision=facts.selection_revision,
            output_rate=output_rate,
            output_channels=output_channels,
            terminal_format=str(terminal_format),
            processing_revision=(int(plan.graph_revision) if plan is not None else 0),
        )
        return ManagedPcmOutputPlan(
            plan_id=f"managed:{execution_id[:24]}",
            stable_device_id=facts.selected_device_id,
            device_locator=locator,
            binding_generation=int(getattr(binding, "generation", 0) or 0),
            source_pcm=source,
            processing_plan_id=processing_plan_id,
            processing_graph_revision=graph_revision,
            processing_revision=(plan.graph_revision if plan is not None else 0),
            working_format=working_format,
            output_rate_hz=output_rate,
            output_channels=output_channels,
            terminal_format=str(terminal_format),
            volume_policy=facts.volume_policy,
            selection_revision=facts.selection_revision,
            execution_id=execution_id,
            transform_policy=transform_policy,
            evidence_refs=(f"terminal:{terminal_format}",),
            path=MANAGED_PCM_PATH,
        )


def _preferred_terminal(proven: frozenset[str]) -> str:
    """Deterministic proven terminal for a route without a compiled plan."""
    normalized = {str(value).strip() for value in proven}
    for candidate in _PREFERRED_TERMINALS:
        if candidate in normalized:
            return candidate
    return sorted(normalized)[0] if normalized else ""


def _transform_policy(plan: CompiledProcessingPlan) -> tuple[str, ...]:
    flags: list[str] = []
    if plan.nodes:
        flags.append("dsp")
    if plan.changes_representation:
        flags.append("representation_conversion")
    if plan.changes_rate:
        flags.append("rate_change")
    if plan.changes_channels:
        flags.append("channel_map")
    if plan.quantization_boundary:
        flags.append("quantization")
    return tuple(flags) if flags else ("identity",)


def _execution_id(
    *,
    plan_id: str | None,
    device_id: str,
    locator: str,
    binding_generation: int,
    selection_revision: int,
    output_rate: int,
    output_channels: int,
    terminal_format: str,
    processing_revision: int,
) -> str:
    material = json.dumps(
        {
            "plan_id": plan_id,
            "device": device_id,
            "locator": locator,
            "binding_generation": binding_generation,
            "selection_revision": selection_revision,
            "rate": output_rate,
            "channels": output_channels,
            "terminal": terminal_format,
            "processing_revision": processing_revision,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
