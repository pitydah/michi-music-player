"""Michi Link API v1 — data models."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ServerInfo:
    service: str = "michi-music-player"
    name: str = "Michi Music Player"
    api_version: str = "v1"
    roles: list[str] = field(default_factory=lambda: [
        "desktop_player", "library_master", "sync_host",
        "remote_control_target", "cast_controller",
    ])
    features: dict[str, bool] = field(default_factory=lambda: {
        "library": True, "search": True, "streaming": True,
        "sync_manifest": True, "remote_control": True,
        "queue": True, "artwork": True, "playlists": True,
        "audio_chains": True, "receivers": True,
        "token_refresh": False, "events": False,
    })

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlaybackStateDto:
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
    tracks: list[dict] = field(default_factory=list)
    current_index: int = -1
    queue_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrackDto:
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
    action: str = ""
    value: Any = None
    seek_ms: float = 0.0
    volume: int = 70


@dataclass
class V1PairStartRequest:
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
    success: bool = False
    device_id: str = ""
    device_token: str = ""
    permissions: list[str] = field(default_factory=list)
    server_device_id: str = ""
    server_alias: str = "Michi Music Player"
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))
