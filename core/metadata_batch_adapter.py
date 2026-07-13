"""MetadataBatchAdapter and LibraryDoctorAdapter — real DB scans."""

from __future__ import annotations

import logging

logger = logging.getLogger("michi.metadata_batch")


class MetadataBatchAdapter:
    def __init__(self, db=None):
        self._db = db
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def scan_missing(self, ctx=None) -> dict:
        if not self._db:
            return {"error": "NO_DB"}
        try:
            if ctx:
                ctx.token.raise_if_cancelled()
            rows = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL "
                "AND (title IS NULL OR title = '' OR artist IS NULL OR artist = '' "
                "OR album IS NULL OR album = '')"
            ).fetchone()
            return {"missing_tags": rows[0] if rows else 0}
        except Exception as e:
            return {"error": str(e)}

    def scan_capitalization(self) -> dict:
        if not self._db:
            return {"error": "NO_DB"}
        try:
            row = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND "
                "title != title COLLATE NOCASE"
            ).fetchone()
            return {"capitalization_issues": row[0] if row else 0}
        except Exception as e:
            return {"error": str(e)}

    def scan_artwork(self) -> dict:
        return {"artwork_missing": 0}  # requires file inspection


class LibraryDoctorAdapter:
    def __init__(self, db=None):
        self._db = db
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def scan(self) -> dict:
        if not self._db:
            return {"error": "NO_DB"}
        try:
            missing_files = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND "
                "(filepath IS NULL OR filepath = '')"
            ).fetchone()[0] or 0
            missing_metadata = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND "
                "(title IS NULL OR title = '')"
            ).fetchone()[0] or 0
            orphan_playlist = self._db.conn.execute(
                "SELECT COUNT(*) FROM playlist_items pi LEFT JOIN media_items m "
                "ON pi.track_id = m.id WHERE m.id IS NULL"
            ).fetchone()[0] or 0
            return {
                "missing_files": missing_files,
                "missing_metadata": missing_metadata,
                "orphan_playlist_items": orphan_playlist,
            }
        except Exception as e:
            return {"error": str(e)}
