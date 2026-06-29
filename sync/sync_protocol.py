"""Sync protocol — data classes for wireless music sync.

Inspired by LocalSend's RegisterDto, FileDto, PrepareUploadRequestDto patterns.
Simplified for music-specific sync: no TLS, token-based auth, JSON over HTTP.
"""

import json
import time
import hashlib
import secrets
from dataclasses import dataclass, field, asdict


# ═══════════════════════════════════════
#  Device & Session
# ═══════════════════════════════════════

@dataclass
class DeviceInfo:
    alias: str
    device: str = "desktop"     # desktop | android
    device_model: str = ""
    port: int = 0
    version: str = "1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "DeviceInfo":
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionToken:
    token: str
    created: float = field(default_factory=time.time)
    device_alias: str = ""
    client_device_id: str = ""
    device_type: str = ""
    device_model: str = ""

    def is_expired(self, max_age: float = 3600.0) -> bool:
        return (time.time() - self.created) > max_age

    @staticmethod
    def generate(device_alias: str = "", client_device_id: str = "",
                 device_type: str = "", device_model: str = "") -> "SessionToken":
        return SessionToken(
            token=secrets.token_hex(32),
            device_alias=device_alias,
            client_device_id=client_device_id,
            device_type=device_type,
            device_model=device_model,
        )


# ═══════════════════════════════════════
#  Music-specific DTOs
# ═══════════════════════════════════════

@dataclass
class TrackDto:
    id: str               # filepath hash or DB id
    title: str
    artist: str = ""
    album: str = ""
    duration: int = 0      # seconds
    size: int = 0          # bytes
    format: str = ""       # "FLAC", "MP3", "DSD64", etc.
    bitrate: int = 0       # bps
    sample_rate: int = 0   # Hz
    channels: int = 0
    cover_id: str = ""     # hash or filename for cover art
    filepath: str = ""     # local path on server (never sent to client)
    track_number: int = 0
    year: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("filepath", None)  # never send local paths
        return d


@dataclass
class LibraryResponse:
    tracks: list[dict]     # list of TrackDto.to_dict()
    total: int
    artists: int = 0
    albums: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class SyncStateEntry:
    track_id: str
    play_count: int = 0
    last_played: float = 0.0   # unix timestamp
    favorite: bool = False


@dataclass
class SyncStateRequest:
    session_token: str
    tracks: list[dict]   # list of SyncStateEntry as dicts

    @classmethod
    def from_json(cls, s: str) -> "SyncStateRequest":
        d = json.loads(s)
        return cls(session_token=d.get("session_token", ""),
                   tracks=d.get("tracks", []))


@dataclass
class RegisterRequest:
    """Legacy — kept for backward compat. PairRequest replaces this."""
    alias: str
    device: str = "android"
    device_model: str = ""
    port: int = 0
    client_device_id: str = ""

    @classmethod
    def from_json(cls, s: str) -> "RegisterRequest":
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


@dataclass
class RegisterResponse:
    """Legacy — kept for backward compat. PairResponse replaces this."""
    session_token: str
    server_device_id: str
    client_device_id: str
    library_size: int
    version: str = "1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# ═══════════════════════════════════════
#  Pairing DTOs (replaces open register)
# ═══════════════════════════════════════

@dataclass
class PairStartRequest:
    alias: str
    device: str = "android"
    device_model: str = ""
    port: int = 0
    client_device_id: str = ""

    @classmethod
    def from_json(cls, s: str) -> "PairStartRequest":
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


@dataclass
class PairStartResponse:
    pairing_id: str = ""
    auth_methods: list[str] = field(default_factory=lambda: ["password"])
    server_alias: str = "Michi Music Player"
    auth_required: bool = True
    server_device_id: str = ""
    version: str = "1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class PairConfirmRequest:
    client_device_id: str
    username: str = ""
    password: str = ""
    pairing_code: str = ""
    alias: str = ""
    device_model: str = ""
    port: int = 0
    client_version: str = ""

    @classmethod
    def from_json(cls, s: str) -> "PairConfirmRequest":
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


@dataclass
class PairConfirmResponse:
    success: bool
    device_id: str = ""
    device_token: str = ""
    refresh_token: str = ""
    permissions: list[str] = field(default_factory=list)
    session_token: str = ""
    server_device_id: str = ""
    server_alias: str = "Michi Music Player"
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# ═══════════════════════════════════════
#  Token & Permission helpers
# ═══════════════════════════════════════

SYNC_PERMISSIONS = {
    "sync.read_manifest",
    "sync.download_tracks",
    "sync.download_covers",
    "sync.download_playlists",
    "sync.upload_state",
    "remote.control",
}


def check_permission(device_permissions: list[str], required: str) -> bool:
    return required in device_permissions


# ═══════════════════════════════════════
#  Discovery (UDP multicast)
# ═══════════════════════════════════════

MULTICAST_GROUP = "224.0.0.167"
MULTICAST_PORT = 53318
SYNC_PORT = 53318        # same port for HTTP server

ANNOUNCE_INTERVAL = 5.0  # seconds between announcements


@dataclass
class AnnounceMessage:
    type: str = "announce"
    alias: str = ""
    device: str = "desktop"
    port: int = SYNC_PORT
    version: str = "1.0"
    device_model: str = ""
    device_id: str = ""
    auth_required: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "AnnounceMessage":
        d = json.loads(s)
        return cls(**{k: v for k, v in d.items()
                     if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════

def make_track_id(filepath: str, track_uid: str = "") -> str:
    """Generate stable track identity for sync manifests.

    Priority:
      1. MusicBrainz Track ID from DB (mb:<uuid>) → strip prefix, use UUID
      2. File-path hash from DB (fp:<sha256_hex16>) → strip prefix, use hash
      3. Fallback: SHA-256 of filepath, first 16 hex chars
    """
    if track_uid and track_uid.startswith("mb:"):
        return track_uid[3:]
    if track_uid and track_uid.startswith("fp:"):
        return track_uid[3:]
    return hashlib.sha256(filepath.encode()).hexdigest()[:16]


def make_cover_id(album: str, artist: str = "") -> str:
    """Stable cover identifier — always SHA-256 of album+artist."""
    raw = f"{album}||{artist}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def make_device_id() -> str:
    """Generate persistent device ID."""
    import os
    from core.paths import app_data_dir
    config_dir = app_data_dir()
    id_file = os.path.join(config_dir, "device_id")
    if os.path.exists(id_file):
        with open(id_file) as f:
            return f.read().strip()
    did = secrets.token_hex(8)
    os.makedirs(config_dir, exist_ok=True)
    with open(id_file, "w") as f:
        f.write(did)
    return did
