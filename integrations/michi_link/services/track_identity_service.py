"""TrackIdentityService — computes stable identity for local tracks.

Used for import preflight (checking if Micro Server already has a track)
and for Continue on Server (resolving local queue to remote track_ids).

Identity includes:
  - quick_hash: SHA-256 of first 64 KB (fast dedup)
  - content_hash: full file SHA-256 (strong verification)
  - file_size, duration_ms, normalized metadata
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from integrations.michi_link.services.result import Result

logger = logging.getLogger("michi.service.track_identity")

QUICK_HASH_LEN = 32  # hex chars


@dataclass
class TrackIdentity:
    local_track_id: str = ""
    quick_hash: str = ""
    content_hash: str = ""
    sha256_prefix: str = ""  # legacy alias for quick_hash
    file_size: int = 0
    duration_ms: float = 0.0
    title: str = ""
    artist: str = ""
    album: str = ""
    normalized_title: str = ""
    normalized_artist: str = ""
    normalized_album: str = ""
    filepath: str = ""

    def __post_init__(self):
        if not self.quick_hash and self.sha256_prefix:
            self.quick_hash = self.sha256_prefix
        if not self.sha256_prefix and self.quick_hash:
            self.sha256_prefix = self.quick_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_track_id": self.local_track_id,
            "quick_hash": self.quick_hash,
            "content_hash": self.content_hash,
            "sha256_prefix": self.sha256_prefix,
            "file_size": self.file_size,
            "duration_ms": self.duration_ms,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "normalized_title": self.normalized_title,
            "normalized_artist": self.normalized_artist,
            "normalized_album": self.normalized_album,
        }

    def match(self, other: TrackIdentity) -> bool:
        """Check if two identities refer to the same track.
        Priority: content_hash > quick_hash > size+duration+normalized.
        """
        if self.content_hash and other.content_hash:
            return self.content_hash == other.content_hash
        if self.quick_hash and other.quick_hash:
            return self.quick_hash == other.quick_hash
        if (self.file_size and other.file_size and self.file_size == other.file_size
                and self.duration_ms and other.duration_ms
                and abs(self.duration_ms - other.duration_ms) < 2000):
            return self._normalized_match(other)
        return False

    def _normalized_match(self, other: TrackIdentity) -> bool:
        return (self.normalized_title == other.normalized_title and
                self.normalized_artist == other.normalized_artist)


def _normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().lower()) if s else ""


def _quick_hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for _ in range(64):
                chunk = f.read(1024)
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:QUICK_HASH_LEN]


def _full_hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


class TrackIdentityService:
    """Computes TrackIdentity for local tracks."""

    def compute(self, filepath: str, db_item: Any = None,
                local_track_id: str = "") -> Result:
        if not filepath or not os.path.isfile(filepath):
            return Result.fail("FILE_NOT_FOUND", f"File not found: {filepath}")

        file_size = os.path.getsize(filepath)
        quick = _quick_hash_file(filepath)
        content = _full_hash_file(filepath)

        title = ""
        artist = ""
        album = ""
        duration_ms = 0.0
        if db_item is not None:
            title = str(getattr(db_item, "title", "") or getattr(db_item, "filename", ""))
            artist = str(getattr(db_item, "artist", "") or "")
            album = str(getattr(db_item, "album", "") or "")
            duration = float(getattr(db_item, "duration", 0) or 0)
            duration_ms = duration * 1000.0

        if not title:
            title = os.path.splitext(os.path.basename(filepath))[0]

        tid = local_track_id or content[:16] or quick or os.path.basename(filepath)

        identity = TrackIdentity(
            local_track_id=tid,
            quick_hash=quick,
            content_hash=content,
            file_size=file_size,
            duration_ms=duration_ms,
            title=title,
            artist=artist,
            album=album,
            normalized_title=_normalize(title),
            normalized_artist=_normalize(artist),
            normalized_album=_normalize(album),
            filepath=filepath,
        )
        return Result.success(identity, f"Identity computed for {tid}")

    def compute_from_dict(self, track_dict: dict,
                          local_track_id: str = "") -> TrackIdentity:
        filepath = track_dict.get("filepath", "")
        title = track_dict.get("title", "")
        artist = track_dict.get("artist", "")
        album = track_dict.get("album", "")
        duration = float(track_dict.get("duration", 0) or 0)
        file_size = int(track_dict.get("size", 0) or 0)

        quick = _quick_hash_file(filepath) if filepath and os.path.isfile(filepath) else ""
        content = _full_hash_file(filepath) if filepath and os.path.isfile(filepath) else ""

        tid = local_track_id or content[:16] or quick or (
            os.path.basename(filepath) if filepath else "")

        return TrackIdentity(
            local_track_id=tid,
            quick_hash=quick,
            content_hash=content,
            file_size=file_size,
            duration_ms=duration * 1000.0,
            title=title,
            artist=artist,
            album=album,
            normalized_title=_normalize(title),
            normalized_artist=_normalize(artist),
            normalized_album=_normalize(album),
            filepath=filepath,
        )

    def identity_to_preflight(self, identity: TrackIdentity) -> dict:
        """Convert identity to a preflight request payload.
        Never exposes filepath.
        """
        return {
            "local_track_id": identity.local_track_id,
            "quick_hash": identity.quick_hash,
            "content_hash": identity.content_hash,
            "file_size": identity.file_size,
            "duration_ms": identity.duration_ms,
            "title": identity.normalized_title,
            "artist": identity.normalized_artist,
            "album": identity.normalized_album,
        }
