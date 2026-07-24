"""TrackActionService — acciones de biblioteca por ID público, sin filepath."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("michi.track_actions")


class TrackActionService:
    def __init__(self, query_service, queue_service, playlist_service, db):
        if query_service is None or queue_service is None:
            raise ValueError("TrackActionService requires query_service and queue_service")
        if playlist_service is None or db is None:
            raise ValueError("TrackActionService requires playlist_service and database")
        self._qs = query_service
        self._queue = queue_service
        self._playlists = playlist_service
        self._db = db

    def _get_track(self, track_id: int) -> dict | None:
        track = self._qs.fetch_track_internal(track_id)
        if not track or not track.get("filepath"):
            return None
        return track

    def play_track(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            result = self._queue.enqueue(track, play_now=True)
            return {**result, "track_id": track_id} if result.get("ok") else result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def enqueue_track(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            result = self._queue.enqueue(track, play_now=False)
            return {**result, "track_id": track_id} if result.get("ok") else result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next(self, track_id: int) -> dict:
        try:
            track = self._get_track(track_id)
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            return self._queue.enqueue_next(track)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, track_id: int, playlist_id: int) -> dict:
        if self._db:
            row = self._db.conn.execute("SELECT 1 FROM playlists WHERE id=?", (playlist_id,)).fetchone()
            if not row:
                return {"ok": False, "error": "PLAYLIST_NOT_FOUND"}
        return self._playlists.add_track(playlist_id, track_id=track_id)

    def reveal_track(self, track_id: int) -> dict:
        if not self._qs:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._qs.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            parent = str(Path(track["filepath"]).parent)
            import subprocess
            import os
            if os.name == "nt":
                subprocess.Popen(["explorer", parent])
            else:
                subprocess.Popen(["xdg-open", parent])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def toggle_favorite(self, track_id: int) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            track = self._qs.fetch_track_internal(track_id) if self._qs else None
            if not track:
                return {"ok": False, "error": "NOT_FOUND"}
            fp = track.get("filepath", "")
            if not fp:
                return {"ok": False, "error": "NO_FILEPATH"}
            row = self._db.conn.execute(
                "SELECT 1 FROM favorites WHERE track_id=?", (fp,)
            ).fetchone()
            if row:
                self._db.conn.execute("DELETE FROM favorites WHERE track_id=?", (fp,))
                fav = False
            else:
                self._db.conn.execute(
                    "INSERT OR IGNORE INTO favorites (track_id) VALUES (?)", (fp,))
                fav = True
            self._db.conn.commit()
            return {"ok": True, "favorite": fav}
        except Exception as e:
            return {"ok": False, "error": str(e)}
