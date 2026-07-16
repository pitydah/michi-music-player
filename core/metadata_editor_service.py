"""MetadataEditorService — batch/single metadata editing with preview and rollback."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.metadata_editor")


class MetadataEditorService:
    def __init__(self, db=None):
        self._db = db

    def preview(self, filepath: str, changes: dict) -> dict:
        return {"ok": True, "filepath": filepath, "changes": changes, "preview": changes}

    def apply(self, filepath: str, changes: dict) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            for key, value in changes.items():
                if key in ("title", "artist", "album", "genre", "year", "track_number"):
                    self._db.conn.execute(
                        f"UPDATE tracks SET {key}=? WHERE filepath=?", (value, filepath))
            return {"ok": True, "applied": list(changes.keys())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rollback(self, filepath: str, field: str, previous_value: Any) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute(
                f"UPDATE tracks SET {field}=? WHERE filepath=?", (previous_value, filepath))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
