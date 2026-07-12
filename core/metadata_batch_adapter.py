"""MetadataBatchAdapter — ejecuta análisis y corrección de metadatos en WorkerManager."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.metadata_batch")


class MetadataBatchAdapter:
    def __init__(self, db=None):
        self._db = db
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def scan_missing(self) -> dict:
        if not self._db:
            return {"error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL "
                "AND (title IS NULL OR title = '' OR artist IS NULL OR artist = '' "
                "OR album IS NULL OR album = '')"
            ).fetchone()
            return {"missing_tags": rows[0] if rows else 0}
        except Exception as e:
            return {"error": str(e)}


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
            return {"missing_files": missing_files, "missing_metadata": missing_metadata}
        except Exception as e:
            return {"error": str(e)}
