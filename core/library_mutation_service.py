from __future__ import annotations

import logging

logger = logging.getLogger("michi.library_mutation")


class LibraryMutationService:
    def __init__(self, db=None, query_service=None):
        self._db = db
        self._qs = query_service

    def update_metadata(self, track_id: int, data: dict) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            fields = []
            values = []
            for k, v in data.items():
                if k in ("title", "artist", "album", "genre", "year", "track", "disc"):
                    fields.append(f"{k}=?")
                    values.append(v)
            if not fields:
                return {"ok": False, "error": "NO_FIELDS"}
            values.append(track_id)
            self._db.conn.execute(
                f"UPDATE media_items SET {','.join(fields)} WHERE id=?",
                values
            )
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def batch_update(self, updates: list[dict]) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        ok = 0
        fail = 0
        for item in updates:
            result = self.update_metadata(item.get("track_id"), item.get("data", {}))
            if result.get("ok"):
                ok += 1
            else:
                fail += 1
        return {"ok": fail == 0, "updated": ok, "failed": fail}
