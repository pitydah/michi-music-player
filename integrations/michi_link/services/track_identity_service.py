"""TrackIdentityService — computes stable identity for local tracks.

Used for import preflight (checking if Micro Server already has a track)
and for Continue on Server (resolving local queue to remote track_ids).

Identity = (sha256_prefix, file_size, duration_ms, normalized_metadata)
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any

from integrations.michi_link.services.result import Result

logger = logging.getLogger("michi.service.track_identity")

IDENTITY_HASH_PREFIX_LEN = 32  # hex chars = 16 bytes


@dataclass
class TrackIdentity:
    local_track_id: str = ""
    sha256_prefix: str = ""
    file_size: int = 0
    duration_ms: float = 0.0
    title: str = ""
    artist: str = ""
    album: str = ""
    normalized_title: str = ""
    normalized_artist: str = ""
    normalized_album: str = ""
    filepath: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_track_id": self.local_track_id,
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
        """Check if two identities refer to the same track."""
        if self.sha256_prefix and other.sha256_prefix:
            return self.sha256_prefix == other.sha256_prefix
        if (self.file_size and other.file_size and self.file_size == other.file_size
                and self.duration_ms and other.duration_ms
                and abs(self.duration_ms - other.duration_ms) < 2000):
            return self._normalized_match(other)
        return False

    def _normalized_match(self, other: TrackIdentity) -> bool:
        return (self.normalized_title == other.normalized_title and
                self.normalized_artist == other.normalized_artist)


def _normalize(s: str) -> str:
    """Normalize a string for comparison: lower, strip, collapse whitespace."""
    import re
    return re.sub(r'\s+', ' ', s.strip().lower())


class TrackIdentityService:
    """Computes TrackIdentity for local tracks."""

    def compute(self, filepath: str, db_item: Any = None,
                local_track_id: str = "") -> Result:
        """Compute identity for a local track file.

        Args:
            filepath: Absolute path to the audio file.
            db_item: Optional DB item with metadata (title, artist, album, duration).
            local_track_id: Optional stable local ID.

        Returns:
            Result with TrackIdentity on success.
        """
        if not filepath or not os.path.isfile(filepath):
            return Result.fail("FILE_NOT_FOUND", f"File not found: {filepath}")

        file_size = os.path.getsize(filepath)

        # SHA-256 partial hash
        sha_prefix = ""
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for _ in range(64):  # first 64KB
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    h.update(chunk)
            sha_prefix = h.hexdigest()[:IDENTITY_HASH_PREFIX_LEN]
        except OSError as e:
            logger.warning("SHA-256 prefix failed for %s: %s", filepath, e)

        # Metadata from DB item or filename
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

        tid = local_track_id or sha_prefix or os.path.basename(filepath)

        identity = TrackIdentity(
            local_track_id=tid,
            sha256_prefix=sha_prefix,
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
        """Compute identity from a dict (e.g., queue item)."""
        import hashlib
        filepath = track_dict.get("filepath", "")
        title = track_dict.get("title", "")
        artist = track_dict.get("artist", "")
        album = track_dict.get("album", "")
        duration = float(track_dict.get("duration", 0) or 0)
        file_size = int(track_dict.get("size", 0) or 0)

        sha_prefix = ""
        if filepath and os.path.isfile(filepath):
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for _ in range(64):
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    h.update(chunk)
            sha_prefix = h.hexdigest()[:IDENTITY_HASH_PREFIX_LEN]

        tid = local_track_id or sha_prefix or os.path.basename(filepath) if filepath else ""

        return TrackIdentity(
            local_track_id=tid,
            sha256_prefix=sha_prefix,
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
        """Convert identity to a preflight request payload."""
        return {
            "sha256_prefix": identity.sha256_prefix,
            "file_size": identity.file_size,
            "duration_ms": identity.duration_ms,
            "title": identity.normalized_title,
            "artist": identity.normalized_artist,
            "album": identity.normalized_album,
        }
