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
    """Engine runtime lifecycle — deliberately distinct from PlaybackStatus.

    engine READY + playback STOPPED is valid; engine READY + playback PLAYING
    is valid; engine FAILED + playback STOPPED is valid."""

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

    local_file_playback: bool = True
    seek: bool = True
    pause: bool = True
    volume: bool = True
    mute: bool = True


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
    capabilities: AudioEngineCapabilities = field(
        default_factory=AudioEngineCapabilities
    )


@dataclass(frozen=True)
class AudioEngineState:
    """Sole engine-state projection (owned by AudioEngineService).

    SELECTED != ACTIVE: selected = user/product intent (persisted later in
    M11.3F); active = the engine currently bound to the transport router.
    selected GSTREAMER + GStreamer unavailable + active QT_MULTIMEDIA is a
    valid state."""

    selected_engine_id: AudioEngineId = AudioEngineId.QT_MULTIMEDIA
    active_engine_id: AudioEngineId | None = None
    lifecycle: AudioEngineLifecycle = AudioEngineLifecycle.UNAVAILABLE
    switching_to: AudioEngineId | None = None
    error_message: str | None = None
    fallback_from: AudioEngineId | None = None
