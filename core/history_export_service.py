"""HistoryExportService — export listening history to JSON/CSV."""
from __future__ import annotations

import csv
import json
import logging

logger = logging.getLogger("michi.history_export")


class HistoryExportService:
    def __init__(self, db=None):
        self._db = db
        self._cancelled = False

    def export_json(self, output_path: str, filters: dict | None = None) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT track_id, title, artist, played_at FROM history "
                "ORDER BY played_at DESC LIMIT 10000").fetchall()
            data = [{"track_id": r[0], "title": r[1], "artist": r[2], "played_at": r[3]} for r in rows]
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            return {"ok": True, "path": output_path, "count": len(data)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_csv(self, output_path: str, filters: dict | None = None) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT track_id, title, artist, played_at FROM history "
                "ORDER BY played_at DESC LIMIT 10000").fetchall()
            with open(output_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["track_id", "title", "artist", "played_at"])
                w.writerows(rows)
            return {"ok": True, "path": output_path, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel_export(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
