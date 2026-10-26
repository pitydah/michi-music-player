"""Generation-safe audio family transition planning (AP2-F10)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class AudioFamily(StrEnum):
    PCM_DIRECT = "PCM_DIRECT"
    NATIVE_DSD = "NATIVE_DSD"
    DOP = "DOP"
    DSD_TO_PCM = "DSD_TO_PCM"


class PlaybackStatus(StrEnum):
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"
    PLAYING = "PLAYING"


class GaplessClass(StrEnum):
    GAPLESS_EXACT = "GAPLESS_EXACT"
    GAPLESS_SAME_GRAPH = "GAPLESS_SAME_GRAPH"
    GAPLESS_DEGRADED_REOPEN = "GAPLESS_DEGRADED_REOPEN"
    NOT_GAPLESS_BY_POLICY = "NOT_GAPLESS_BY_POLICY"


class TransitionError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FamilyTransitionRequest:
    media_identity: str
    source_family: AudioFamily
    target_family: AudioFamily
    predecessor_status: PlaybackStatus
    request_epoch: int
    current_epoch: int
    output_generation: int
    processing_generation: int
    binding_generation: int
    destructive_boundary: bool
    confirmed_position_ms: int | None = None


@dataclass(frozen=True, slots=True)
class FamilyTransitionReceipt:
    media_identity: str
    source_family: AudioFamily
    target_family: AudioFamily
    request_epoch: int
    predecessor_status: PlaybackStatus
    confirmed_position_ms: int | None
    output_generation: int
    processing_generation: int
    binding_generation: int
    destructive_boundary: bool
    predecessor_released: bool
    gapless: GaplessClass
    resume_status: PlaybackStatus


@dataclass(frozen=True, slots=True)
class TransitionFailure:
    status: PlaybackStatus
    reason: str
    restored: bool


class AudioFamilyTransitionService:
    """Plan transitions; OutputSession/Playback remain the authorities."""

    def plan(self, request: FamilyTransitionRequest) -> FamilyTransitionReceipt:
        if request.request_epoch <= request.current_epoch:
            raise TransitionError("TRANSITION_EPOCH_STALE", "request epoch not newer")
        if request.source_family is request.target_family:
            raise TransitionError("TRANSITION_SAME_FAMILY", "not a family change")
        if request.source_family in (AudioFamily.NATIVE_DSD, AudioFamily.DOP) and (
            request.target_family is AudioFamily.DSD_TO_PCM
        ):
            pass  # allowed only as an explicit policy-approved transition
        if request.target_family in (AudioFamily.NATIVE_DSD, AudioFamily.DOP) and (
            request.source_family is AudioFamily.DSD_TO_PCM
        ):
            pass
        gapless = (
            GaplessClass.GAPLESS_DEGRADED_REOPEN
            if request.destructive_boundary
            else GaplessClass.NOT_GAPLESS_BY_POLICY
        )
        resume = request.predecessor_status
        if resume is not PlaybackStatus.PLAYING:
            # PAUSED and STOPPED never become autoplay after a reopen.
            resume = request.predecessor_status
        return FamilyTransitionReceipt(
            media_identity=request.media_identity,
            source_family=request.source_family,
            target_family=request.target_family,
            request_epoch=request.request_epoch,
            predecessor_status=request.predecessor_status,
            confirmed_position_ms=request.confirmed_position_ms,
            output_generation=request.output_generation,
            processing_generation=request.processing_generation,
            binding_generation=request.binding_generation,
            destructive_boundary=request.destructive_boundary,
            predecessor_released=False,
            gapless=gapless,
            resume_status=resume,
        )

    def mark_released(
        self, receipt: FamilyTransitionReceipt
    ) -> FamilyTransitionReceipt:
        return replace(receipt, predecessor_released=True)

    def on_failure(
        self,
        request: FamilyTransitionRequest,
        *,
        rollback_safe: bool,
        reason: str,
    ) -> TransitionFailure:
        if rollback_safe and request.predecessor_status is not PlaybackStatus.STOPPED:
            return TransitionFailure(
                status=request.predecessor_status, reason=reason, restored=True
            )
        return TransitionFailure(
            status=PlaybackStatus.STOPPED, reason=reason, restored=False
        )
