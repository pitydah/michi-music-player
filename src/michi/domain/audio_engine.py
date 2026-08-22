"""Multi-engine audio runtime domain contracts (M11.3A).

Pure domain: no Qt, no GStreamer, no MPD, no SQLite, no infrastructure
imports. Persistence-safe canonical ids."""

from dataclasses import dataclass, field
from enum import Enum


class AudioEngineId(Enum):
    """Canonical engine identities — persistence-safe string values."""

    QT_MULTIMEDIA = "qt_multimedia"
    GSTREAMER = "gstreamer"
    MPD = "mpd"


class AudioEngineLifecycle(Enum):
    """Engine RUNTIME SLOT lifecycle — deliberately distinct from
    PlaybackStatus and from the SELECTED descriptor.

    UNINITIALIZED = startup before any activation (initial state).
    UNAVAILABLE   = the activation layer recognized the target cannot
                    activate (dependency missing).
    AVAILABLE     = an activatable engine is recognized but not yet
                    READY/bound.
    INITIALIZING  = target initialization underway.
    READY         = transport bound and validated.
    FAILED        = activation/startup failed (error_message set).
    CLOSING       = teardown in progress.

    engine READY + playback STOPPED is valid; engine FAILED + playback
    STOPPED is valid. The lifecycle axis NEVER describes PlaybackStatus."""

    UNINITIALIZED = "uninitialized"
    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"
    CLOSING = "closing"


@dataclass(frozen=True)
class AudioEngineCapabilities:
    """M11.3 transport/runtime capabilities ONLY.

    M11.4/M11.5 capabilities (DSD, DoP, bitPerfect, exclusive, hardwareVolume,
    sampleRates, deviceIds, DAC) deliberately do NOT belong here."""

    # Conservative defaults: UNKNOWN != TRUE. Implemented adapters must
    # explicitly supply their truthful transport capabilities (Qt provider
    # does); probe-only providers (GStreamer/MPD before C/D) keep these
    # conservative values until their adapters exist.
    local_file_playback: bool = False
    seek: bool = False
    pause: bool = False
    volume: bool = False
    mute: bool = False


@dataclass(frozen=True)
class AudioEngineDescriptor:
    """Truthful availability descriptor.

    available means the runtime dependency can be used on THIS machine —
    NOT that it is selected, active or playing. implemented distinguishes
    dependency availability from implementation readiness (a provider may be
    installed but its adapter not yet implemented)."""

    engine_id: AudioEngineId
    display_name: str
    available: bool
    unavailable_reason: str | None = None
    implemented: bool = True
    implementation_reason: str | None = None
    capabilities: AudioEngineCapabilities = field(
        default_factory=AudioEngineCapabilities
    )

    @property
    def can_activate(self) -> bool:
        """ACTIVATABLE = AVAILABLE AND IMPLEMENTED.

        RUNTIME PRESENT != IMPLEMENTATION READY != ACTIVATABLE."""
        return self.available and self.implemented

    @property
    def activation_blocker(self) -> str | None:
        """Exact reason why the engine cannot be activated, or None."""
        if not self.available:
            return self.unavailable_reason or "runtime unavailable"
        if not self.implemented:
            return self.implementation_reason or "engine adapter not implemented"
        return None


@dataclass(frozen=True)
class AudioEngineState:
    """Sole engine-state projection (owned by AudioEngineService).

    SELECTED != ACTIVE: selected = user/product intent (persisted later in
    M11.3F); active = the engine currently bound to the transport router.
    selected GSTREAMER + GStreamer unavailable + active QT_MULTIMEDIA is a
    valid state."""

    selected_engine_id: AudioEngineId = AudioEngineId.QT_MULTIMEDIA
    active_engine_id: AudioEngineId | None = None
    lifecycle: AudioEngineLifecycle = AudioEngineLifecycle.UNINITIALIZED
    switching_to: AudioEngineId | None = None
    error_message: str | None = None
    fallback_from: AudioEngineId | None = None
