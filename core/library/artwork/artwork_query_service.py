"""ArtworkQueryService — SQL queries for artwork scanning extracted from ui/audio_lab/artwork_page.py."""
from __future__ import annotations
import logging

logger = logging.getLogger("michi.artwork_query")


class ArtworkQueryService:
    def __init__(self, db=None):
        self._db = db

    def get_album_artist_dirs(self) -> list[tuple[str, str, str]]:
        if self._db is None:
            return []
        try:
            rows = self._db._conn.execute(
                "SELECT DISTINCT album, albumartist, directory "
                "FROM media_items WHERE deleted_at IS NULL "
                "AND album IS NOT NULL AND album != ''"
            ).fetchall()
            return [(r[0], r[1], r[2]) for r in rows]
        except Exception:
            logger.exception("get_album_artist_dirs failed")
            return []
