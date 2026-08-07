"""TrackActionService executes through an explicit ActionContext (Slice 3).

Real sqlite database for track resolution, a recording queue for readback,
real FavoriteService and PlaylistService-backed playlist stub: the service
must never consult a global selection — the context is the target.
"""
from __future__ import annotations

import sqlite3

from core.action_context import ActionContext
from core.favorite_service import FavoriteService
from core.track_action_service import TrackActionService
from library.schema import Schema


class _Db:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn


class _QueryService:
    """Minimal query surface used by TrackActionService over the real DB."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def fetch_track_internal(self, track_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT id, filepath, title, artist, album, duration, track_uid, "
            "album_key FROM media_items WHERE id=? AND deleted_at IS NULL",
            (track_id,),
        ).fetchone()
        if not row:
            return None
        return {"track_id": row[0], "filepath": row[1], "title": row[2] or "",
                "artist": row[3] or "", "album": row[4] or "",
                "duration": row[5] or 0, "track_uid": row[6] or "",
                "album_key": row[7] or ""}

    def fetch_track_by_uid(self, track_uid: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, filepath, title, artist, album, duration, track_uid, "
            "album_key FROM media_items WHERE track_uid=? AND deleted_at IS NULL",
            (track_uid,),
        ).fetchone()
        if not row:
            return None
        return {"track_id": row[0], "filepath": row[1], "title": row[2] or "",
                "artist": row[3] or "", "album": row[4] or "",
                "duration": row[5] or 0, "track_uid": row[6] or "",
                "album_key": row[7] or ""}

    def fetch_track_by_filepath(self, filepath: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, filepath, title, artist, album, duration, track_uid, "
            "album_key FROM media_items WHERE filepath=? AND deleted_at IS NULL",
            (filepath,),
        ).fetchone()
        if not row:
            return None
        return {"track_id": row[0], "filepath": row[1], "title": row[2] or "",
                "artist": row[3] or "", "album": row[4] or "",
                "duration": row[5] or 0, "track_uid": row[6] or "",
                "album_key": row[7] or ""}


class _QueueService:
    """Recording queue — readback proves the context track was enqueued."""

    def __init__(self):
        self._tracks: list[dict] = []
        self.play_now_flags: list[bool] = []

    def enqueue(self, items, play_now: bool = False) -> dict:
        if isinstance(items, dict):
            items = [items]
        self._tracks.extend(items)
        self.play_now_flags.append(play_now)
        return {"ok": True, "added": len(items)}

    def enqueue_next(self, items) -> dict:
        if isinstance(items, dict):
            items = [items]
        self._tracks.extend(items)
        return {"ok": True, "next": 1}

    def tracks(self) -> list[dict]:
        return list(self._tracks)


class _Playlists:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self.added: list[tuple[int, int]] = []

    def get_detail(self, pid: int) -> dict:
        row = self._conn.execute(
            "SELECT 1 FROM playlists WHERE id=?", (pid,)).fetchone()
        return {"ok": row is not None} if row else {"ok": False, "error": "NOT_FOUND"}

    def add_track(self, pid: int, track_id: int = 0, filepath: str = "") -> dict:
        self.added.append((pid, track_id))
        return {"ok": True, "playlist_id": pid, "track_id": track_id}


def _stack():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    conn.execute(
        "INSERT INTO playlists (name) VALUES ('Test')")
    conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "album_key, track_uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("/m/one.flac", "one.flac", "/m", ".flac", "audio", "One",
             "Artist A", "Album A", "album-a", "uid-1"),
            ("/m/two.flac", "two.flac", "/m", ".flac", "audio", "Two",
             "Artist A", "Album A", "album-a", "uid-2"),
        ],
    )
    conn.commit()
    db = _Db(conn)
    query = _QueryService(conn)
    queue = _QueueService()
    playlists = _Playlists(conn)
    favorites = FavoriteService(db=db)
    svc = TrackActionService(
        query_service=query,
        queue_service=queue,
        playlist_service=playlists,
        db=db,
        favorite_service=favorites,
    )
    return conn, db, query, queue, playlists, svc


def test_enqueue_context_track_by_uid() -> None:
    _conn, _db, _query, queue, _playlists, svc = _stack()
    context = ActionContext(entity_type="track", entity_id="uid-2",
                            public_ref="track_2", selection_version=1)
    result = svc.enqueue_context(context)
    assert result["ok"] is True
    assert result["track_id"] == 2
    assert [t["track_uid"] for t in queue.tracks()] == ["uid-2"]


def test_play_context_uses_play_now() -> None:
    _conn, _db, _query, queue, _playlists, svc = _stack()
    context = ActionContext(entity_type="track", entity_id="uid-1")
    result = svc.play_context(context)
    assert result["ok"] is True
    assert queue.play_now_flags == [True]


def test_enqueue_context_unknown_entity_fails() -> None:
    _conn, _db, _query, queue, _playlists, svc = _stack()
    context = ActionContext(entity_type="track", entity_id="no-such-uid")
    result = svc.enqueue_context(context)
    assert result == {"ok": False, "code": "NOT_FOUND",
                      "error": "Track not found for context"}


def test_toggle_favorite_delegates_to_favorite_service() -> None:
    conn, db, _query, _queue, _playlists, svc = _stack()
    result = svc.toggle_favorite(1)
    assert result == {"ok": True, "favorite": True}
    row = conn.execute(
        "SELECT track_id, entity_id FROM favorites").fetchone()
    assert row == ("/m/one.flac", "uid-1")
    toggled = svc.toggle_favorite(1)
    assert toggled == {"ok": True, "favorite": False}
    assert db.conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0] == 0


def test_add_to_playlist_delegates_existence_check() -> None:
    _conn, _db, _query, _queue, playlists, svc = _stack()
    ok = svc.add_to_playlist(1, 1)
    assert ok == {"ok": True, "playlist_id": 1, "track_id": 1}
    missing = svc.add_to_playlist(1, 999)
    assert missing == {"ok": False, "error": "PLAYLIST_NOT_FOUND"}
