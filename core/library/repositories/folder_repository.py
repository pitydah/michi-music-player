from __future__ import annotations

import sqlite3
from typing import Any


class FolderRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def tree(self, parent_path: str = "") -> list[dict[str, Any]]:
        if parent_path:
            like = f"{parent_path}/%"
            rows = self._conn().execute(
                "SELECT DISTINCT directory, COUNT(*) as cnt "
                "FROM media_items "
                "WHERE deleted_at IS NULL AND directory LIKE ? "
                "AND directory NOT LIKE ? "
                "GROUP BY directory ORDER BY directory",
                (like, f"{parent_path}/%/%"),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT DISTINCT directory, COUNT(*) as cnt "
                "FROM media_items "
                "WHERE deleted_at IS NULL "
                "GROUP BY directory ORDER BY directory",
            ).fetchall()
        return [{"path": r[0], "name": (r[0] or "").rsplit("/", 1)[-1] if "/" in (r[0] or "") else r[0],
                 "track_count": r[1]} for r in rows]

    def children(self, parent_path: str) -> list[dict[str, Any]]:
        like = f"{parent_path}/%"
        rows = self._conn().execute(
            "SELECT DISTINCT directory, COUNT(*) as cnt "
            "FROM media_items "
            "WHERE deleted_at IS NULL AND directory LIKE ? "
            "AND directory NOT LIKE ? "
            "GROUP BY directory ORDER BY directory",
            (like, f"{parent_path}/%/%"),
        ).fetchall()
        return [{"path": r[0], "name": (r[0] or "").rsplit("/", 1)[-1] if "/" in (r[0] or "") else r[0],
                 "track_count": r[1]} for r in rows]

    def parents(self, path: str) -> list[dict[str, Any]]:
        parts = [p for p in path.split("/") if p]
        result = []
        for i in range(1, len(parts)):
            ancestor = "/".join(parts[:i])
            result.append({"path": ancestor, "name": parts[i - 1]})
        return result

    def breadcrumb(self, path: str) -> list[dict[str, str]]:
        parts = [p for p in path.split("/") if p]
        crumbs = []
        for i in range(1, len(parts) + 1):
            ancestor = "/".join(parts[:i])
            crumbs.append({"path": ancestor, "name": parts[i - 1]})
        return crumbs

    def count(self, parent_path: str = "") -> int:
        if parent_path:
            like = f"{parent_path}/%"
            row = self._conn().execute(
                "SELECT COUNT(DISTINCT directory) FROM media_items "
                "WHERE deleted_at IS NULL AND directory LIKE ? "
                "AND directory NOT LIKE ?",
                (like, f"{parent_path}/%/%"),
            ).fetchone()
        else:
            row = self._conn().execute(
                "SELECT COUNT(DISTINCT directory) FROM media_items "
                "WHERE deleted_at IS NULL",
            ).fetchone()
        return row[0] if row else 0
