"""ImportStore — server-side storage for Michi Link import sessions.

The MichiLinkServer accepts track/artwork/playlist uploads scoped to an import
session. Sessions are pending until ``commit`` marks them committed; rollback
discards all uploaded items. Every stored item keeps its SHA-256 checksum so
clients can verify uploads by readback (``/api/v1/import/track/info``).

Committed sessions are persisted to a SQLite ledger (debt D3a): a server
restart must not lose the record of committed uploads. The in-memory map is
the working cache; the ledger is written on ``commit`` and cleared on
``rollback``/``drop``, and reloaded when a store is created with the same
``db_path``. The ledger stores session/item METADATA (checksums, sizes,
filenames) — raw upload bytes remain transient and are not restored.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
import contextlib
from dataclasses import dataclass, field
from pathlib import Path

SESSION_TTL_SECONDS = 3600

_LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS import_sessions (
    session_id   TEXT PRIMARY KEY,
    payload      TEXT NOT NULL,
    committed_at REAL NOT NULL
)
"""


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
    """Holds import sessions keyed by session id.

    ``db_path`` enables the SQLite committed-session ledger (debt D3a). When
    ``None`` the store is memory-only, preserving the original behavior.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._sessions: dict[str, ImportSessionRecord] = {}
        self._load_persisted()

    # ── SQLite ledger ──

    def _ensure_conn(self) -> sqlite3.Connection | None:
        if self._db_path is None:
            return None
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute(_LEDGER_SCHEMA)
            self._conn.commit()
        return self._conn

    def _load_persisted(self) -> None:
        conn = self._ensure_conn()
        if conn is None:
            return
        try:
            rows = conn.execute(
                "SELECT session_id, payload, committed_at FROM import_sessions"
            ).fetchall()
        except sqlite3.Error:
            return
        for session_id, payload, _committed_at in rows:
            session = self._restore_session(payload)
            if session is not None:
                self._sessions[session_id] = session

    def _session_payload(self, session: ImportSessionRecord) -> str:
        """Ledger payload: session + item metadata, never raw bytes."""
        return json.dumps({
            "session_id": session.session_id,
            "state": session.state,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
            "committed_at": session.committed_at,
            "source": session.source,
            "tracks": [
                {
                    "track_id": t.track_id, "filename": t.filename,
                    "checksum": t.checksum, "size": t.size,
                    "uploaded_at": t.uploaded_at,
                }
                for t in session.tracks.values()
            ],
            "artwork": [
                {
                    "cover_id": a.cover_id, "checksum": a.checksum,
                    "size": a.size, "uploaded_at": a.uploaded_at,
                }
                for a in session.artwork.values()
            ],
            "playlists": [
                {
                    "playlist_id": p.playlist_id, "name": p.name,
                    "track_ids": list(p.track_ids),
                }
                for p in session.playlists.values()
            ],
        })

    def _restore_session(self, payload: str) -> ImportSessionRecord | None:
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return None
        session = ImportSessionRecord(
            session_id=data.get("session_id", ""),
            state=data.get("state", "committed"),
            created_at=data.get("created_at", 0.0),
            expires_at=data.get("expires_at", 0.0),
            committed_at=data.get("committed_at", 0.0),
            source=data.get("source", ""),
        )
        for t in data.get("tracks", []):
            session.tracks[t["track_id"]] = StoredTrack(
                track_id=t["track_id"], filename=t.get("filename", ""),
                data=b"", checksum=t.get("checksum", ""),
                size=t.get("size", 0), uploaded_at=t.get("uploaded_at", 0.0),
            )
        for a in data.get("artwork", []):
            session.artwork[a["cover_id"]] = StoredArtwork(
                cover_id=a["cover_id"], data=b"",
                checksum=a.get("checksum", ""), size=a.get("size", 0),
                uploaded_at=a.get("uploaded_at", 0.0),
            )
        for p in data.get("playlists", []):
            session.playlists[p["playlist_id"]] = StoredPlaylist(
                playlist_id=p["playlist_id"], name=p.get("name", ""),
                track_ids=list(p.get("track_ids", [])),
            )
        return session

    def _persist(self, session: ImportSessionRecord) -> None:
        conn = self._ensure_conn()
        if conn is None:
            return
        try:
            conn.execute(
                "INSERT OR REPLACE INTO import_sessions "
                "(session_id, payload, committed_at) VALUES (?, ?, ?)",
                (session.session_id, self._session_payload(session),
                 session.committed_at),
            )
            conn.commit()
        except sqlite3.Error:
            return

    def _delete_persisted(self, session_id: str) -> None:
        conn = self._ensure_conn()
        if conn is None:
            return
        try:
            conn.execute(
                "DELETE FROM import_sessions WHERE session_id=?", (session_id,)
            )
            conn.commit()
        except sqlite3.Error:
            return

    def close(self) -> None:
        """Close the underlying ledger connection, if any."""
        if self._conn is not None:
            with contextlib.suppress(Exception):
                self._conn.close()
            self._conn = None

    # ── Session API ──

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
        self._persist(session)
        return session

    def rollback(self, session_id: str) -> ImportSessionRecord | None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return None
        session.state = "rolled_back"
        self._delete_persisted(session_id)
        return session

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._delete_persisted(session_id)

    def prune_expired(self) -> int:
        """Remove expired pending sessions; returns the number dropped."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired
        ]
        for sid in expired:
            self.drop(sid)
        return len(expired)
