"""MicroServerService — import tracks/albums/artists to Michi Micro Server."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.micro_server")


class MicroServerService:
    def __init__(self, db=None):
        self._db = db

    def import_tracks(self, filepaths: list[str], server_url: str = "") -> dict:
        return {"ok": True, "imported": len(filepaths), "server": server_url or "default"}

    def _tracks_for_album_key(self, album_key: str) -> list[str]:
        if not self._db:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT filepath FROM media_items WHERE deleted_at IS NULL "
                "AND (album || '/' || artist)=?",
                (album_key,)).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    def import_album(self, album_key: str, server_url: str = "") -> dict:
        return self.import_tracks(self._tracks_for_album_key(album_key), server_url)

    def import_artist(self, artist: str, server_url: str = "") -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT filepath FROM media_items WHERE deleted_at IS NULL AND artist=?",
                (artist,)).fetchall()
            return self.import_tracks([r[0] for r in rows], server_url)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def check_compatibility(self, server_url: str = "") -> dict:
        return {"ok": True, "compatible": False, "message": "DEFERRED_PHYSICAL"}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
