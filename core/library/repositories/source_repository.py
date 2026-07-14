from __future__ import annotations

import sqlite3
import time
from typing import Any


class SourceRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def get_all(self) -> list[dict[str, Any]]:
        try:
            rows = self._conn().execute(
                "SELECT id, path, enabled, last_scan, file_count, "
                "added_count, updated_count, skipped_count, missing_count, "
                "created_at, updated_at "
                "FROM library_roots ORDER BY path"
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        keys = ["id", "path", "enabled", "last_scan", "file_count",
                "added_count", "updated_count", "skipped_count", "missing_count",
                "created_at", "updated_at"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def get_by_id(self, source_id: int) -> dict[str, Any] | None:
        row = self._conn().execute(
            "SELECT id, path, enabled, last_scan, file_count, "
            "added_count, updated_count, skipped_count, missing_count, "
            "created_at, updated_at "
            "FROM library_roots WHERE id=?",
            (source_id,),
        ).fetchone()
        if not row:
            return None
        keys = ["id", "path", "enabled", "last_scan", "file_count",
                "added_count", "updated_count", "skipped_count", "missing_count",
                "created_at", "updated_at"]
        return dict(zip(keys, row, strict=False))

    def create(self, path: str, enabled: bool = True) -> int:
        conn = self._conn()
        now = time.time()
        cur = conn.execute(
            "INSERT INTO library_roots (path, enabled, created_at, updated_at) "
            "VALUES (?,?,?,?)",
            (path, int(enabled), now, now),
        )
        conn.commit()
        return cur.lastrowid

    def update(self, source_id: int, **kwargs) -> bool:
        conn = self._conn()
        allowed = {"path", "enabled", "last_scan", "file_count",
                   "added_count", "updated_count", "skipped_count", "missing_count"}
        cols = [k for k in kwargs if k in allowed]
        if not cols:
            return False
        vals = [kwargs[k] for k in cols]
        vals.append(time.time())
        vals.append(source_id)
        conn.execute(
            f"UPDATE library_roots SET "
            f"{','.join(f'{c}=?' for c in cols)}, updated_at=? WHERE id=?",
            vals,
        )
        conn.commit()
        return True

    def delete(self, source_id: int) -> bool:
        conn = self._conn()
        cur = conn.execute(
            "DELETE FROM library_roots WHERE id=?",
            (source_id,),
        )
        conn.commit()
        return cur.rowcount > 0

    def enable(self, source_id: int) -> bool:
        conn = self._conn()
        cur = conn.execute(
            "UPDATE library_roots SET enabled=1, updated_at=? WHERE id=?",
            (time.time(), source_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def disable(self, source_id: int) -> bool:
        conn = self._conn()
        cur = conn.execute(
            "UPDATE library_roots SET enabled=0, updated_at=? WHERE id=?",
            (time.time(), source_id),
        )
        conn.commit()
        return cur.rowcount > 0

    def scan_status(self, source_id: int) -> dict[str, Any]:
        row = self._conn().execute(
            "SELECT last_scan, file_count, added_count, "
            "updated_count, skipped_count, missing_count "
            "FROM library_roots WHERE id=?",
            (source_id,),
        ).fetchone()
        if not row:
            return {}
        keys = ["last_scan", "file_count", "added_count",
                "updated_count", "skipped_count", "missing_count"]
        return dict(zip(keys, row, strict=False))

    def counts(self) -> dict[str, int]:
        total = self._conn().execute(
            "SELECT COUNT(*) FROM library_roots",
        ).fetchone()[0]
        enabled = self._conn().execute(
            "SELECT COUNT(*) FROM library_roots WHERE enabled=1",
        ).fetchone()[0]
        return {"total": total or 0, "enabled": enabled or 0}
