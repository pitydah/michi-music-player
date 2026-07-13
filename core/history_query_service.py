"""HistoryQueryService — paginated play history via SQL JOIN, no full load."""
from __future__ import annotations

import logging


logger = logging.getLogger("michi.history_query")


class HistoryQueryService:
    def __init__(self, db=None):
        self._db = db

    def count_history(self, artist: str = "", album: str = "") -> int:
        if not self._db:
            return 0
        try:
            where, params = self._build_where(artist, album)
            row = self._db.conn.execute(
                f"SELECT COUNT(*) FROM play_history h "
                f"LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                f"WHERE 1=1 {where}", params
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def fetch_history(self, offset: int = 0, limit: int = 100,
                      artist: str = "", album: str = "") -> list[dict]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(artist, album)
            rows = self._db.conn.execute(
                f"SELECT h.track_id, h.played_at, h.device, "
                f"m.id, m.title, m.artist, m.album, m.album_key, m.duration, m.track_uid "
                f"FROM play_history h "
                f"LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                f"WHERE 1=1 {where} "
                f"ORDER BY h.played_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [
                {
                    "track_id": r[3] or 0, "track_uid": r[9] or "",
                    "title": r[4] or r[0] or "", "artist": r[5] or "",
                    "album": r[6] or "", "album_key": r[7] or "",
                    "duration": r[8] or 0, "played_at": r[1] or "",
                    "device": r[2] or "",
                }
                for r in rows
            ]
        except Exception:
            return []

    def remove_history_item(self, track_id: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history WHERE track_id=?", (track_id,))
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_history(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history")
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_history_enabled(self, enabled: bool) -> dict:
        return {"ok": True}

    def set_history_limit(self, limit: int) -> dict:
        return {"ok": True}

    def _build_where(self, artist: str = "", album: str = "") -> tuple[str, list]:
        clauses = []
        params = []
        if artist:
            clauses.append("(m.artist = ? OR m.albumartist = ?)")
            params.extend([artist, artist])
        if album:
            clauses.append("(m.album = ? OR m.album_key = ?)")
            params.extend([album, album])
        where = "AND " + " AND ".join(clauses) if clauses else ""
        return where, params
