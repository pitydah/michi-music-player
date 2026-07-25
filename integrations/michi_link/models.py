"""Michi Link API v1 — data models."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ServerInfo:
    """Describe this player's Michi Link identity and advertised capabilities."""

    service: str = "michi-music-player"
    name: str = "Michi Music Player"
    api_version: str = "v1"
    version: str = "1.0.0"
    michi_link_version: str = "1.0.0-alpha"
    roles: list[str] = field(default_factory=lambda: [
        "desktop_player", "library_master", "sync_host",
        "remote_control_target", "cast_controller",
    ])
    auth: dict = field(default_factory=lambda: {
        "required": True,
        "strategy": "PLAYER_PASSWORD",
        "token_refresh": False,
    })
    features: dict[str, bool] = field(default_factory=lambda: {
        "library": True, "search": True, "streaming": True,
        "sync_manifest": True, "remote_control": True,
        "queue": True, "artwork": True, "playlists": True,
        "token_refresh": False, "events": False,
        "receivers": False, "rooms": False,
    })

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlaybackStateDto:
    """Represent the player's current playback state for API responses."""

    state: str = "stopped"  # playing | paused | stopped
    current_track: dict | None = None
    position_ms: float = 0.0
    duration_ms: float = 0.0
    volume: int = 70
    shuffle: bool = False
    repeat: str = "none"  # none | one | all
    queue_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["position_ms"] = round(d["position_ms"], 1)
        d["duration_ms"] = round(d["duration_ms"], 1)
        return d


@dataclass
class QueueDto:
    """Represent the ordered playback queue and its current selection."""

    tracks: list[dict] = field(default_factory=list)
    current_index: int = -1
    queue_id: str = ""
    repeat: str = "none"
    shuffle: bool = False
    revision: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrackDto:
    """Represent track metadata exposed through the Michi Link API."""

    track_id: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    cover_id: str = ""
    download_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ControlRequest:
    """Describe a remote playback control action and its optional value."""

    action: str = ""
    value: Any = None
    seek_ms: float = 0.0
    volume: int = 70


@dataclass
class V1PairStartRequest:
    """Carry client device details when starting a v1 pairing session."""

    client_device_id: str = ""
    alias: str = ""
    device_model: str = ""
    port: int = 0
    client_version: str = ""

    @classmethod
    def from_json(cls, s: str) -> V1PairStartRequest:
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


@dataclass
class V1PairStartResponse:
    """Return pairing session details and supported authentication methods."""

    pairing_id: str = ""
    auth_methods: list[str] = field(default_factory=lambda: ["password"])
    server_alias: str = "Michi Music Player"
    auth_required: bool = True
    server_device_id: str = ""
    version: str = "1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class V1PairConfirmRequest:
    """Carry client credentials and device details to confirm v1 pairing."""

    client_device_id: str = ""
    username: str = ""
    password: str = ""
    alias: str = ""
    device_model: str = ""
    port: int = 0
    client_version: str = ""

    @classmethod
    def from_json(cls, s: str) -> V1PairConfirmRequest:
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


@dataclass
class V1PairConfirmResponse:
    """Report the result, token, and permissions granted by v1 pairing."""

    success: bool = False
    device_id: str = ""
    device_token: str = ""
    permissions: list[str] = field(default_factory=list)
    server_device_id: str = ""
    server_alias: str = "Michi Music Player"
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))
