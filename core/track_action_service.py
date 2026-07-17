"""TrackActionService — acciones de biblioteca por ID público, sin filepath."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("michi.track_actions")


class TrackActionService:
    def __init__(self, query_service=None, player_service=None,
                 library_bridge=None, playlist_bridge=None, db=None):
        self._qs = query_service
        self._player = player_service
        self._lib = library_bridge
        self._pl = playlist_bridge
        self._db = db

    def play_track(self, track_id: int) -> dict:
        if not self._qs:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._qs.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            if not self._player:
                return {"ok": False, "error": "NO_PLAYER"}
            fp = track["filepath"]
            if hasattr(self._player, 'enqueue'):
                self._player.enqueue([fp], play_now=True)
            elif hasattr(self._player, 'play_file'):
                self._player.play_file(fp)
            else:
                return {"ok": False, "error": "NO_PLAY_METHOD"}
            return {"ok": True, "track_id": track_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def enqueue_track(self, track_id: int) -> dict:
        if not self._qs:
            return {"ok": False, "error": "NO_QUERY_SERVICE"}
        try:
            track = self._qs.fetch_track_internal(track_id)
            if not track or not track.get("filepath"):
                return {"ok": False, "error": "NOT_FOUND"}
            if not self._player or not hasattr(self._player, 'enqueue'):
                return {"ok": False, "error": "UNSUPPORTED"}
            self._player.enqueue([track["filepath"]], play_now=False)
            return {"ok": True, "track_id": track_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def play_next(self, track_id: int) -> dict:
        if not self._player or not hasattr(self._player, 'enqueue_next'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            track = self._qs.fetch_track_internal(track_id) if self._qs else None
            if track and track.get("filepath"):
                self._player.enqueue_next(track["filepath"])
                return {"ok": True}
            return {"ok": False, "error": "NOT_FOUND"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, track_id: int, playlist_id: int) -> dict:
        if not self._pl:
            return {"ok": False, "error": "NO_PLAYLIST_BRIDGE"}
        if self._db:
            row = self._db.conn.execute("SELECT 1 FROM playlists WHERE id=?", (playlist_id,)).fetchone()
            if not row:
                return {"ok": False, "error": "PLAYLIST_NOT_FOUND"}
        return self._pl.addTrackToPlaylist(playlist_id, track_id=str(track_id))

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
