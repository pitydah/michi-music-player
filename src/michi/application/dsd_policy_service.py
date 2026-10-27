"""Single DSD/DSP decision policy (AP2-F10, R11-F10)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from michi.application.dsd_to_pcm_plan import QUALITY_RATE_LADDERS
from michi.domain.dsd_signal import DsdSignalFormat


class SourceKind(StrEnum):
    PCM = "PCM"
    DSD = "DSD"


class DsdIntent(StrEnum):
    PCM_DIRECT = "PCM_DIRECT"
    PCM_PROCESSED = "PCM_PROCESSED"
    NATIVE_DSD = "NATIVE_DSD"
    DOP = "DOP"
    PRESERVE_DSD = "PRESERVE_DSD"
    CONVERT_TO_PCM = "CONVERT_TO_PCM"
    PROCESS_AS_PCM = "PROCESS_AS_PCM"
    AUTO = "AUTO"


class OutputFamily(StrEnum):
    PCM_DIRECT = "PCM_DIRECT"
    PCM_PROCESSED = "PCM_PROCESSED"
    NATIVE_DSD = "NATIVE_DSD"
    DOP = "DOP"
    DSD_TO_PCM = "DSD_TO_PCM"
    DSD_TO_PCM_DSP = "DSD_TO_PCM_DSP"
    REFUSED = "REFUSED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class DsdPolicyRequest:
    source_kind: SourceKind
    source_identity: str
    source_format: DsdSignalFormat | None
    intent: DsdIntent | str
    dsp_requested: bool
    conversion_consent: bool
    source_truth_verified: bool = False
    decoder_available: bool = False
    target_qualified: bool = False
    dsp_available: bool = False
    native_available: bool = False
    dop_available: bool = False
    quality_profile: str = "HIGH"
    request_epoch: int = 0
    current_epoch: int | None = None
    processing_graph_revision: int | None = None
    current_processing_graph_revision: int | None = None
    binding_generation: int = 0
    current_binding_generation: int | None = None


@dataclass(frozen=True, slots=True)
class DsdPolicyDecision:
    decision: OutputFamily
    reason: str
    reasons: tuple[str, ...]
    conversion_consent_required: bool
    quality_profile: str | None
    target_rate_hz: int | None = None


class DsdPolicyService:
    """Decide only; output/session/planner authorities remain unchanged."""

    def decide(self, request: DsdPolicyRequest) -> DsdPolicyDecision:
        intent = DsdIntent(request.intent)
        if not isinstance(request.source_kind, SourceKind):
            raise TypeError("source_kind must be a SourceKind")
        stale = self._stale_reason(request)
        if stale:
            return self._unavailable(stale, request)
        if request.source_kind is SourceKind.PCM:
            if intent is DsdIntent.PCM_PROCESSED:
                if not request.dsp_available:
                    return self._unavailable("DSP_UNAVAILABLE", request)
                return self._decision(OutputFamily.PCM_PROCESSED, "PCM_DSP", request)
            if intent is DsdIntent.PCM_DIRECT:
                if request.dsp_requested:
                    return self._refused("PCM_DSP_INTENT_REQUIRED", request)
                return self._decision(OutputFamily.PCM_DIRECT, "PCM_DIRECT", request)
            return self._refused("PCM_INTENT_INCOMPATIBLE", request)
        if not request.source_truth_verified:
            return self._unavailable("DSD_SOURCE_TRUTH_REQUIRED", request)
        if request.source_format is None:
            return self._unavailable("DSD_SOURCE_FORMAT_REQUIRED", request)
        if request.quality_profile not in QUALITY_RATE_LADDERS:
            return self._refused("QUALITY_PROFILE_UNKNOWN", request)
        if intent is DsdIntent.PRESERVE_DSD:
            if request.dsp_requested:
                return self._refused("DSP_ON_PRESERVE_DSD", request)
            if not request.native_available:
                return self._unavailable("NATIVE_DSD_UNAVAILABLE", request)
            return self._decision(
                OutputFamily.NATIVE_DSD, "PRESERVE_DSD_BYPASS", request
            )
        if intent is DsdIntent.NATIVE_DSD:
            if request.dsp_requested:
                return self._refused("DSP_ON_NATIVE_DSD", request)
            if not request.native_available:
                return self._unavailable("NATIVE_DSD_UNAVAILABLE", request)
            return self._decision(OutputFamily.NATIVE_DSD, "NATIVE_DSD", request)
        if intent is DsdIntent.DOP:
            if request.dsp_requested:
                return self._refused("DSP_ON_DOP_CARRIER", request)
            if not request.dop_available:
                return self._unavailable("DOP_UNAVAILABLE", request)
            return self._decision(OutputFamily.DOP, "DOP_EXPLICIT", request)
        if intent is DsdIntent.AUTO:
            if request.conversion_consent:
                return self._unavailable("AUTO_CANNOT_DECIDE", request)
            if not request.native_available:
                return self._unavailable("NATIVE_DSD_UNAVAILABLE", request)
            return self._decision(
                OutputFamily.NATIVE_DSD, "AUTO_PRESERVES_DSD", request
            )
        if intent not in (
            DsdIntent.CONVERT_TO_PCM,
            DsdIntent.PROCESS_AS_PCM,
            DsdIntent.AUTO,
        ):
            return self._refused("INTENT_UNKNOWN", request)
        if not request.conversion_consent:
            return self._refused("CONVERSION_CONSENT_REQUIRED", request)
        if not request.source_truth_verified:
            return self._unavailable("DSD_SOURCE_TRUTH_REQUIRED", request)
        if not request.decoder_available:
            return self._unavailable("DSD_PCM_DECODER_UNAVAILABLE", request)
        if not request.target_qualified:
            return self._unavailable("DSD_PCM_TARGET_UNQUALIFIED", request)
        wants_dsp = request.dsp_requested or intent is DsdIntent.PROCESS_AS_PCM
        if wants_dsp and not request.dsp_available:
            return self._unavailable("DSD_PCM_DSP_UNAVAILABLE", request)
        if wants_dsp:
            return self._decision(
                OutputFamily.DSD_TO_PCM_DSP, "DSD_TO_PCM_DSP", request
            )
        return self._decision(OutputFamily.DSD_TO_PCM, "DSD_TO_PCM", request)

    @staticmethod
    def _stale_reason(request: DsdPolicyRequest) -> str | None:
        if request.current_epoch is not None:
            if request.request_epoch < request.current_epoch:
                return "REQUEST_EPOCH_STALE"
            if request.request_epoch == request.current_epoch:
                return "REQUEST_EPOCH_DUPLICATE"
        if (
            request.current_processing_graph_revision is not None
            and request.processing_graph_revision
            != request.current_processing_graph_revision
        ):
            return "PROCESSING_GRAPH_STALE"
        if (
            request.current_binding_generation is not None
            and request.binding_generation != request.current_binding_generation
        ):
            return "BINDING_GENERATION_STALE"
        return None

    @staticmethod
    def _decision(
        decision: OutputFamily, reason: str, request: DsdPolicyRequest
    ) -> DsdPolicyDecision:
        return DsdPolicyDecision(
            decision=decision,
            reason=reason,
            reasons=(reason,),
            conversion_consent_required=(
                request.source_kind is SourceKind.DSD
                and decision in (OutputFamily.DSD_TO_PCM, OutputFamily.DSD_TO_PCM_DSP)
                and not request.conversion_consent
            ),
            quality_profile=request.quality_profile,
        )

    def _refused(self, reason: str, request: DsdPolicyRequest) -> DsdPolicyDecision:
        return DsdPolicyDecision(
            decision=OutputFamily.REFUSED,
            reason=reason,
            reasons=(reason,),
            conversion_consent_required=reason == "CONVERSION_CONSENT_REQUIRED",
            quality_profile=request.quality_profile,
        )

    def _unavailable(self, reason: str, request: DsdPolicyRequest) -> DsdPolicyDecision:
        return DsdPolicyDecision(
            decision=OutputFamily.UNAVAILABLE,
            reason=reason,
            reasons=(reason,),
            conversion_consent_required=False,
            quality_profile=request.quality_profile,
        )
