"""ImportStore — server-side storage for Michi Link import sessions.

The MichiLinkServer accepts track/artwork/playlist uploads scoped to an import
session. Sessions are pending until ``commit`` marks them committed; rollback
discards all uploaded items. Every stored item keeps its SHA-256 checksum so
clients can verify uploads by readback (``/api/v1/import/track/info``).

The store is in-memory on purpose: an import session is a transient
transaction. Persisting committed uploads to the server library is a separate
(import) step owned by the consuming application.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

SESSION_TTL_SECONDS = 3600


@dataclass
class StoredTrack:
    """An uploaded track held by the server for a session."""

    track_id: str = ""
    filename: str = ""
    data: bytes = b""
    checksum: str = ""
    size: int = 0
    uploaded_at: float = 0.0


@dataclass
class StoredArtwork:
    """An uploaded cover image held by the server for a session."""

    cover_id: str = ""
    data: bytes = b""
    checksum: str = ""
    size: int = 0
    uploaded_at: float = 0.0


@dataclass
class StoredPlaylist:
    """An uploaded playlist held by the server for a session."""

    playlist_id: str = ""
    name: str = ""
    track_ids: list[str] = field(default_factory=list)


@dataclass
class ImportSessionRecord:
    """Server-side state of one import session."""

    session_id: str = ""
    state: str = "pending"  # pending | committed | rolled_back | expired
    created_at: float = 0.0
    expires_at: float = 0.0
    committed_at: float = 0.0
    source: str = ""
    tracks: dict[str, StoredTrack] = field(default_factory=dict)
    artwork: dict[str, StoredArtwork] = field(default_factory=dict)
    playlists: dict[str, StoredPlaylist] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return self.state == "pending" and time.time() > self.expires_at

    def to_public_dict(self) -> dict:
        """Public status payload (no file bytes)."""
        return {
            "session_id": self.session_id,
            "state": self.state,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "committed_at": self.committed_at,
            "source": self.source,
            "uploaded_tracks": len(self.tracks),
            "artwork_count": len(self.artwork),
            "playlist_count": len(self.playlists),
            "playlists": [
                {
                    "playlist_id": p.playlist_id,
                    "name": p.name,
                    "track_count": len(p.track_ids),
                }
                for p in self.playlists.values()
            ],
        }


class ImportStore:
    """Holds import sessions keyed by session id."""

    def __init__(self) -> None:
        self._sessions: dict[str, ImportSessionRecord] = {}

    def create_session(self, source: str = "michi-music-player",
                       ttl: float = SESSION_TTL_SECONDS) -> ImportSessionRecord:
        session = ImportSessionRecord(
            session_id=uuid.uuid4().hex[:12],
            source=source,
            created_at=time.time(),
            expires_at=time.time() + ttl,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ImportSessionRecord | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired:
            session.state = "expired"
            return session
        return session

    def add_track(self, session_id: str, track_id: str, data: bytes,
                  checksum: str = "", filename: str = "") -> StoredTrack | None:
        session = self.get(session_id)
        if session is None or session.state != "pending":
            return None
        stored = StoredTrack(
            track_id=track_id, filename=filename or track_id, data=data,
            checksum=checksum, size=len(data), uploaded_at=time.time(),
        )
        session.tracks[track_id] = stored
        return stored

    def add_artwork(self, session_id: str, cover_id: str, data: bytes,
                    checksum: str = "") -> StoredArtwork | None:
        session = self.get(session_id)
        if session is None or session.state != "pending":
            return None
        stored = StoredArtwork(
            cover_id=cover_id, data=data, checksum=checksum, size=len(data),
            uploaded_at=time.time(),
        )
        session.artwork[cover_id] = stored
        return stored

    def add_playlist(self, session_id: str, playlist_id: str, name: str,
                     track_ids: list[str]) -> StoredPlaylist | None:
        session = self.get(session_id)
        if session is None or session.state != "pending":
            return None
        stored = StoredPlaylist(
            playlist_id=playlist_id, name=name, track_ids=list(track_ids),
        )
        session.playlists[playlist_id] = stored
        return stored

    def track_info(self, session_id: str, track_id: str) -> dict | None:
        session = self.get(session_id)
        if session is None:
            return None
        track = session.tracks.get(track_id)
        if track is None:
            return None
        return {
            "track_id": track.track_id,
            "checksum": track.checksum,
            "size": track.size,
            "filename": track.filename,
            "session_id": session_id,
            "stored": True,
        }

    def track_data(self, session_id: str, track_id: str) -> StoredTrack | None:
        session = self.get(session_id)
        if session is None:
            return None
        return session.tracks.get(track_id)

    def commit(self, session_id: str) -> ImportSessionRecord | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.state == "expired":
            return session
        if session.state != "pending":
            return session
        session.state = "committed"
        session.committed_at = time.time()
        return session

    def rollback(self, session_id: str) -> ImportSessionRecord | None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return None
        session.state = "rolled_back"
        return session

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def prune_expired(self) -> int:
        """Remove expired pending sessions; returns the number dropped."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired
        ]
        for sid in expired:
            self.drop(sid)
        return len(expired)
