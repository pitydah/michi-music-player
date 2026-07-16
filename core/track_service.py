"""TrackService — individual track operations, locate, convert."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.track_service")


class TrackService:
    def __init__(self, db=None, playback_service=None):
        self._db = db
        self._playback = playback_service

    def locate_file(self, filepath: str) -> dict:
        if not filepath:
            return {"ok": False, "error": "NO_PATH"}
        exists = os.path.exists(filepath)
        return {"ok": True, "exists": exists, "path": filepath,
                "dir": os.path.dirname(filepath) if exists else ""}

    def edit_metadata(self, filepath: str, metadata: dict) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            for key, value in metadata.items():
                if key in ("title", "artist", "album", "genre", "year", "track"):
                    col = key
                    self._db.conn.execute(
                        f"UPDATE tracks SET {col}=? WHERE filepath=?", (value, filepath))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def add_to_playlist(self, filepath: str, playlist_id: int) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute(
                "INSERT INTO playlist_tracks (playlist_id, filepath) VALUES (?, ?)",
                (playlist_id, filepath))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
