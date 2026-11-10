"""Remote playback substrate models (E9) — substrate only, no local authority.

Shapes mirror the authoritative endpoints (``GET /api/v1/playback/state`` and
``POST /api/v1/playback/control`` in michi-micro-server). The Player's own
playback authorities are never touched or recreated (master plan §156).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RemoteCommand(StrEnum):
    """Canonical commands accepted by the remote playback endpoint."""

    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    TOGGLE = "toggle"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK = "seek"
    SET_VOLUME = "set_volume"
    MUTE = "mute"
    UNMUTE = "unmute"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"


class RepeatMode(StrEnum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


def _int_or_none(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


@dataclass(frozen=True)
class PlaybackTrack:
    track_id: str
    title: str
    artist: str = ""
    album: str = ""
    duration_ms: int | None = None


@dataclass(frozen=True)
class PlaybackSnapshot:
    """Projection of the remote playback state (functional fields from the API)."""

    state: str
    playing: bool
    position_ms: int
    repeat: str = ""
    track: PlaybackTrack | None = None
    duration_ms: int | None = None
    volume: int | None = None
    shuffle: bool | None = None
    generation_id: int | None = None
    updated_at: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PlaybackSnapshot:
        track: PlaybackTrack | None = None
        raw_track = payload.get("current_track")
        if isinstance(raw_track, Mapping):
            track = PlaybackTrack(
                track_id=str(raw_track.get("id", "")),
                title=str(raw_track.get("title", "")),
                artist=str(raw_track.get("artist", "")),
                album=str(raw_track.get("album", "")),
                duration_ms=_int_or_none(raw_track.get("duration_ms")),
            )
        shuffle = payload.get("shuffle")
        updated = payload.get("updated_at")
        return cls(
            state=str(payload.get("state", "")),
            playing=bool(payload.get("playing", False)),
            position_ms=_int_or_none(payload.get("position_ms")) or 0,
            repeat=str(payload.get("repeat", "")),
            track=track,
            duration_ms=_int_or_none(payload.get("duration_ms")),
            volume=_int_or_none(payload.get("volume")),
            shuffle=shuffle if isinstance(shuffle, bool) else None,
            generation_id=_int_or_none(payload.get("generation_id")),
            updated_at=str(updated) if updated is not None else None,
        )


@dataclass(frozen=True)
class CommandOutcome:
    command: str
    status: str
    payload: Mapping[str, Any] = field(default_factory=dict)
