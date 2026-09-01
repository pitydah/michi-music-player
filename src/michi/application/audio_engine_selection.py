"""Framework-free semantic models for explicit audio-engine selection."""

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_engine import AudioEngineId


class EngineSelectionAction(Enum):
    """The physical meaning of one user engine-selection intent."""

    NOOP = "noop"
    PREFERENCE_ONLY = "preference_only"
    RUNTIME_SWITCH = "runtime_switch"
    RETRY_PREFERRED = "retry_preferred"
    UNAVAILABLE = "unavailable"


class EngineSwitchBlocker(Enum):
    """Typed reason why an engine-selection action cannot start now."""

    USER_MEDIA_REQUEST_PENDING = "user_media_request_pending"
    STARTUP_RESTORE_PENDING = "startup_restore_pending"
    SWITCH_IN_PROGRESS = "switch_in_progress"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"


class MediaRequestPurpose(Enum):
    """Why PlaybackService currently owns a media request."""

    USER_PLAY = "user_play"
    STARTUP_RESTORE = "startup_restore"
    ENGINE_SWITCH_REHYDRATION = "engine_switch_rehydration"


class MediaRequestTerminalStatus(Enum):
    """Terminal outcomes for post-switch stopped-media preparation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class EngineSwitchReadiness:
    allowed: bool
    blocker: EngineSwitchBlocker | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class EngineSelectionPlan:
    target: AudioEngineId
    action: EngineSelectionAction
    allowed: bool
    blocker: EngineSwitchBlocker | None = None
    blocker_detail: str | None = None

    @property
    def blocker_message(self) -> str:
        if self.blocker is EngineSwitchBlocker.USER_MEDIA_REQUEST_PENDING:
            return "Wait for the current track request to finish."
        if self.blocker is EngineSwitchBlocker.STARTUP_RESTORE_PENDING:
            return "Wait for playback restoration to finish."
        if self.blocker is EngineSwitchBlocker.SWITCH_IN_PROGRESS:
            return "Audio engine change is already in progress."
        if self.blocker is EngineSwitchBlocker.RUNTIME_UNAVAILABLE:
            return self.blocker_detail or "This audio engine is not available."
        return ""


@dataclass(frozen=True, slots=True)
class MediaRequestTerminalResult:
    purpose: MediaRequestPurpose
    status: MediaRequestTerminalStatus
    file_path: str
    message: str | None = None
