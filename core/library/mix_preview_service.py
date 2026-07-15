"""MixPreviewService — SQL queries for smart mix previews extracted from ui/controllers/smart_mix_preview.py."""
from __future__ import annotations
import logging

logger = logging.getLogger("michi.mix_preview")


class MixPreviewService:
    def __init__(self, db=None):
        self._db = db

    def favorites(self, limit: int = 30) -> list[str]:
        if self._db is None:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT m.filepath FROM favorites f "
                "LEFT JOIN media_items m ON f.track_id = m.filepath OR f.track_id = CAST(m.id AS TEXT) "
                "WHERE m.deleted_at IS NULL AND m.filepath IS NOT NULL "
                "ORDER BY f.added_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            logger.exception("favorites query failed")
            return []

    def recent(self, limit: int = 30) -> list[str]:
        if self._db is None:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT m.filepath FROM play_history h "
                "LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                "WHERE m.deleted_at IS NULL AND m.filepath IS NOT NULL "
                "ORDER BY h.played_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            logger.exception("recent query failed")
            return []
