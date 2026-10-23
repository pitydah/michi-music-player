"""AP2-F09 — pure DoP planner V3 (double gate: carrier + interpretation).

Carrier qualification and DAC DoP interpretation are deliberately separate.
PCM 176.4/24 capability alone never selects DoP. The planner opens no device.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.domain.dop import (
    DOP_CORE_CHANNELS,
    DOP_PACKER_REVISION,
    PRODUCTION_DOP_LAYOUTS,
    DopCarrierLayout,
    DopCarrierMemoryContract,
    DopCarrierQualification,
    DopCarrierSupport,
    DopDeviceInterpretationEvidence,
    DopInterpretationState,
    DopPackingError,
    DopPolicyDecision,
    interpretation_rank,
    memory_contract_for,
    stable_dop_plan_hash,
    validate_stereo_source,
)
from michi.domain.dsd_signal import DopCarrierRate, DsdSignalFormat, source_to_dop_rate


class DopPlannerError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DopExecutionPlanV2:
    plan_id: str
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    source: DsdSignalFormat
    carrier_rate: DopCarrierRate
    memory_contract: DopCarrierMemoryContract
    packer_revision: str
    carrier_evidence_refs: tuple[str, ...]
    interpretation_evidence_refs: tuple[str, ...]
    interpretation_state: DopInterpretationState
    decision_codes: tuple[str, ...]


class DopPlannerV3:
    def plan(
        self,
        *,
        stable_device_id: str,
        binding_locator: str,
        binding_generation: int,
        source: DsdSignalFormat,
        carrier_qualifications: tuple[DopCarrierQualification, ...],
        interpretation: tuple[DopDeviceInterpretationEvidence, ...],
        policy: DopPolicyDecision,
        layout_preference: tuple[DopCarrierLayout, ...] = PRODUCTION_DOP_LAYOUTS,
        processing_active: bool = False,
        volume_authority: str = "hardware",
        active_engine_id: str = "gstreamer",
        binding_current: bool = True,
    ) -> DopExecutionPlanV2:
        if not isinstance(stable_device_id, str) or not stable_device_id.strip():
            raise DopPlannerError("DOP_DEVICE_MISSING", "stable device id required")
        if not isinstance(binding_locator, str) or not binding_locator.strip():
            raise DopPlannerError("DOP_BINDING_MISSING", "binding locator required")
        if (
            not isinstance(binding_generation, int)
            or isinstance(binding_generation, bool)
            or binding_generation < 0
        ):
            raise DopPlannerError(
                "DOP_BINDING_GENERATION_INVALID", "generation must be non-negative"
            )
        if not isinstance(source, DsdSignalFormat):
            raise DopPlannerError(
                "DOP_SOURCE_INVALID", "source must be DsdSignalFormat"
            )
        try:
            validate_stereo_source(source)
        except DopPackingError as exc:
            raise DopPlannerError(exc.code, exc.detail) from exc
        if not isinstance(policy, DopPolicyDecision):
            raise DopPlannerError("DOP_POLICY_INVALID", "policy is required")
        if processing_active:
            raise DopPlannerError(
                "DOP_DSP_UNSUPPORTED",
                "DoP carrier cannot traverse PCM DSP",
            )
        if str(volume_authority).lower() == "software":
            raise DopPlannerError(
                "DOP_VOLUME_AUTHORITY_UNSUPPORTED",
                "software volume would mutate the DoP carrier",
            )
        if active_engine_id != "gstreamer":
            raise DopPlannerError(
                "DOP_ENGINE_UNSUPPORTED", "DoP requires the GStreamer engine"
            )
        if not binding_current:
            raise DopPlannerError(
                "DOP_BINDING_STALE", "the selected DAC binding is no longer current"
            )
        if not policy.explicit_requested and not policy.auto_allowed:
            raise DopPlannerError(
                "DOP_NOT_ENABLED",
                "DoP requires explicit enablement or an auto-allowed policy",
            )

        interpretation_evidence = self._resolve_interpretation(
            stable_device_id, interpretation, policy
        )
        try:
            rate = source_to_dop_rate(source.source_rate)
        except ValueError as exc:
            raise DopPlannerError("DOP_SOURCE_RATE_INVALID", str(exc)) from exc

        matches = tuple(
            item
            for item in carrier_qualifications
            if item.stable_device_id == stable_device_id
            and item.carrier_rate_hz == rate.frames_per_second
            and item.channels == DOP_CORE_CHANNELS
            and (
                item.binding_generation is None
                or item.binding_generation == binding_generation
            )
        )
        qualified = tuple(
            item for item in matches if item.support is DopCarrierSupport.QUALIFIED
        )
        if not qualified:
            if matches and all(
                item.support
                in (DopCarrierSupport.UNKNOWN, DopCarrierSupport.INCONCLUSIVE)
                for item in matches
            ):
                raise DopPlannerError(
                    "DOP_CARRIER_UNKNOWN",
                    "carrier qualification is unknown/inconclusive",
                )
            if matches and any(
                item.support is DopCarrierSupport.UNSUPPORTED for item in matches
            ):
                raise DopPlannerError(
                    "DOP_CARRIER_UNSUPPORTED",
                    "the exact carrier tuple is unsupported",
                )
            raise DopPlannerError(
                "DOP_CARRIER_LAYOUT_UNQUALIFIED",
                f"no exact carrier layout qualified at {rate.frames_per_second} Hz",
            )

        by_layout: dict[str, DopCarrierQualification] = {}
        for item in qualified:
            if item.carrier_layout_id not in by_layout:
                by_layout[item.carrier_layout_id] = item
        selected_layout = None
        selected_qualification = None
        for layout in layout_preference:
            item = by_layout.get(layout.value)
            if item is not None:
                selected_layout = layout
                selected_qualification = item
                break
        if selected_layout is None or selected_qualification is None:
            raise DopPlannerError(
                "DOP_CARRIER_LAYOUT_UNKNOWN",
                "no preferred qualified carrier layout",
            )
        try:
            memory = memory_contract_for(selected_layout)
        except DopPackingError as exc:
            raise DopPlannerError(exc.code, exc.detail) from exc

        canonical = {
            "stable_device_id": stable_device_id,
            "binding_locator": binding_locator,
            "binding_generation": binding_generation,
            "source": {
                "bit_rate_hz": source.bit_rate_hz,
                "channels": source.channels,
                "packing": source.packing.value,
                "bit_order": source.bit_order.value,
                "organization": source.organization.value,
                "layout": list(source.layout),
            },
            "carrier_rate_hz": rate.frames_per_second,
            "layout": memory.layout.value,
            "alsa_format": memory.alsa_format,
            "carrier_evidence": list(selected_qualification.evidence_refs),
            "interpretation_state": interpretation_evidence.state.value,
            "interpretation_evidence": list(interpretation_evidence.evidence_refs),
            "packer_revision": DOP_PACKER_REVISION,
        }
        plan_id = stable_dop_plan_hash(canonical)
        decisions = [
            "DOP_CARRIER_QUALIFIED",
            "DOP_STEREO_CORE",
            f"DOP_INTERPRETATION_{interpretation_evidence.state.value.upper()}",
        ]
        return DopExecutionPlanV2(
            plan_id=plan_id,
            stable_device_id=stable_device_id,
            binding_locator=binding_locator,
            binding_generation=binding_generation,
            source=source,
            carrier_rate=rate,
            memory_contract=memory,
            packer_revision=DOP_PACKER_REVISION,
            carrier_evidence_refs=selected_qualification.evidence_refs,
            interpretation_evidence_refs=interpretation_evidence.evidence_refs,
            interpretation_state=interpretation_evidence.state,
            decision_codes=tuple(decisions),
        )

    @staticmethod
    def _resolve_interpretation(
        stable_device_id: str,
        evidence: tuple[DopDeviceInterpretationEvidence, ...],
        policy: DopPolicyDecision,
    ) -> DopDeviceInterpretationEvidence:
        matches = tuple(
            item for item in evidence if item.stable_device_id == stable_device_id
        )
        if any(item.state is DopInterpretationState.CONTRADICTED for item in matches):
            raise DopPlannerError(
                "DOP_DEVICE_INTERPRETATION_CONTRADICTED",
                "DoP interpretation is contradicted for this DAC",
            )
        required = interpretation_rank(policy.minimum_interpretation_state)
        if policy.explicit_requested:
            allowed = {
                DopInterpretationState.DECLARED,
                DopInterpretationState.USER_CONFIRMED,
                DopInterpretationState.DEVICE_OBSERVED,
                DopInterpretationState.PHYSICALLY_QUALIFIED,
            }
        else:
            allowed = {
                DopInterpretationState.DEVICE_OBSERVED,
                DopInterpretationState.PHYSICALLY_QUALIFIED,
            }
            if not policy.auto_allowed:
                raise DopPlannerError(
                    "DOP_NOT_ENABLED", "auto DoP is not allowed by policy"
                )
        accepted = [
            item
            for item in matches
            if item.state in allowed and interpretation_rank(item.state) >= required
        ]
        if not accepted:
            raise DopPlannerError(
                "DOP_DEVICE_INTERPRETATION_UNKNOWN",
                "insufficient DoP interpretation evidence for the selected policy",
            )
        return sorted(
            accepted, key=lambda item: interpretation_rank(item.state), reverse=True
        )[0]
