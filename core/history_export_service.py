"""HistoryExportService — export listening history to JSON/CSV.

Durable-job friendly: filters payload (date_from/date_to, artist, album,
device, search), atomic writes (temp file + os.replace), optional
cooperative cancellation via a TaskContext-like ``ctx``, and a manifest
(schema_version, generated_at, filters, row_count) attached to every export.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
import time

logger = logging.getLogger("michi.history_export")

SCHEMA_VERSION = 1


class HistoryExportService:
    def __init__(self, db=None):
        self._db = db
        self._cancelled = False

    def export_history(self, output_path: str, fmt: str = "json",
                       filters: dict | None = None, ctx=None) -> dict:
        if fmt == "csv":
            return self.export_csv(output_path, filters=filters, ctx=ctx)
        return self.export_json(output_path, filters=filters, ctx=ctx)

    def export_json(self, output_path: str, filters: dict | None = None,
                    ctx=None) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        if ctx:
            ctx.token.raise_if_cancelled()
        try:
            rows = self._fetch_rows(filters, ctx)
            if ctx:
                ctx.token.raise_if_cancelled()
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "filters": dict(filters or {}),
                "row_count": len(rows),
                "rows": rows,
            }
            self._atomic_write(
                output_path, lambda f: json.dump(manifest, f, indent=2,
                                                 ensure_ascii=False)
            )
            return {
                "ok": True, "path": output_path, "count": len(rows),
                "schema_version": SCHEMA_VERSION,
                "generated_at": manifest["generated_at"],
                "filters": manifest["filters"],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_csv(self, output_path: str, filters: dict | None = None,
                   ctx=None) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        if ctx:
            ctx.token.raise_if_cancelled()
        try:
            rows = self._fetch_rows(filters, ctx)
            if ctx:
                ctx.token.raise_if_cancelled()

            def write_csv(f):
                w = csv.writer(f)
                w.writerow(["track_id", "title", "artist", "album",
                            "played_at", "device"])
                w.writerows(rows)

            self._atomic_write(output_path, write_csv)
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "filters": dict(filters or {}),
                "row_count": len(rows),
            }
            self._atomic_write(
                output_path + ".manifest.json",
                lambda f: json.dump(manifest, f, indent=2, ensure_ascii=False),
            )
            return {
                "ok": True, "path": output_path, "count": len(rows),
                "schema_version": SCHEMA_VERSION,
                "generated_at": manifest["generated_at"],
                "filters": manifest["filters"],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _fetch_rows(self, filters: dict | None, ctx=None) -> list[dict]:
        where, params = self._build_where(filters or {})
        rows = self._db.conn.execute(
            "SELECT h.track_id, h.played_at, h.device, "
            "m.title, m.artist, m.album "
            "FROM play_history h "
            "LEFT JOIN media_items m ON h.track_id = m.filepath "
            "OR h.track_id = CAST(m.id AS TEXT) "
            f"WHERE 1=1 {where} "
            "ORDER BY h.played_at DESC LIMIT 10000",
            params,
        ).fetchall()
        return [
            {
                "track_id": r[0], "played_at": r[1], "device": r[2] or "",
                "title": r[3] or "", "artist": r[4] or "", "album": r[5] or "",
            }
            for r in rows
        ]

    def _build_where(self, filters: dict) -> tuple[str, list]:
        where = []
        params: list = []
        if filters.get("date_from"):
            where.append("h.played_at >= ?")
            params.append(self._to_ts(filters["date_from"]))
        if filters.get("date_to"):
            where.append("h.played_at <= ?")
            params.append(self._to_ts(filters["date_to"]))
        if filters.get("device"):
            where.append("h.device = ?")
            params.append(filters["device"])
        if filters.get("artist"):
            where.append("m.artist LIKE ?")
            params.append(f"%{filters['artist']}%")
        if filters.get("album"):
            where.append("m.album LIKE ?")
            params.append(f"%{filters['album']}%")
        if filters.get("search"):
            where.append("(m.title LIKE ? OR m.artist LIKE ? OR m.album LIKE ?)")
            params.extend([f"%{filters['search']}%"] * 3)
        clause = (" AND " + " AND ".join(where)) if where else ""
        return clause, params

    @staticmethod
    def _to_ts(value) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return time.mktime(time.strptime(text, fmt))
            except ValueError:
                continue
        try:
            return float(text)
        except ValueError:
            return 0.0

    @staticmethod
    def _atomic_write(output_path: str, writer_fn) -> None:
        directory = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=".michi-export-", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer_fn(f)
            os.replace(tmp_path, output_path)
        except Exception:
            import contextlib
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
            raise

    def cancel_export(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
