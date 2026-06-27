"""Action log — local audit trail for confirmed Michi Assistant actions."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time

logger = logging.getLogger("michi.ai_assistant.action_log")

_LOG_DIR = os.path.expanduser("~/.local/share/michi/ai_assistant")  # legacy compat


def _default_log_dir() -> str:
    from core.paths import ai_assistant_dir
    return ai_assistant_dir()

_LOG_PATH = os.path.join(_default_log_dir(), "actions.sqlite")


class ActionLog:
    def __init__(self, db_path: str = _LOG_PATH, enabled: bool = True):
        self._enabled = enabled
        if not enabled:
            return
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS action_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  REAL NOT NULL,
            tool_name  TEXT NOT NULL,
            permission_level TEXT NOT NULL DEFAULT '',
            summary    TEXT NOT NULL DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'confirmed',
            affected_count INTEGER DEFAULT 0,
            reversible INTEGER DEFAULT 1,
            metadata_json TEXT DEFAULT '{}'
        )""")
        self._conn.commit()

    def register(self, tool_name: str, summary: str = "",
                 status: str = "confirmed", affected_count: int = 0,
                 permission_level: str = "REVERSIBLE",
                 metadata: dict | None = None):
        if not self._enabled:
            return
        try:
            now = time.time()
            meta_safe = _safe_meta(metadata)
            self._conn.execute(
                "INSERT INTO action_log (timestamp, tool_name, permission_level, "
                "summary, status, affected_count, metadata_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (now, tool_name, permission_level or "",
                 summary, status, affected_count,
                 json.dumps(meta_safe, ensure_ascii=False)),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("ActionLog register failed: %s", e)

    def get_recent(self, limit: int = 20) -> list[dict]:
        if not self._enabled:
            return []
        try:
            rows = self._conn.execute(
                "SELECT id, timestamp, tool_name, permission_level, "
                "summary, status, affected_count "
                "FROM action_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "id": r[0], "timestamp": r[1], "tool_name": r[2],
                    "permission_level": r[3], "summary": r[4],
                    "status": r[5], "affected_count": r[6],
                }
                for r in rows
            ]
        except Exception:
            return []

    def total_actions(self) -> int:
        if not self._enabled:
            return 0
        try:
            return self._conn.execute(
                "SELECT COUNT(*) FROM action_log"
            ).fetchone()[0]
        except Exception:
            return 0

    def close(self):
        if self._enabled and hasattr(self, "_conn"):
            self._conn.close()


def _safe_meta(meta: dict | None) -> dict:
    if not meta:
        return {}
    forbidden = {"filepath", "directory", "token", "password", "secret", "api_key"}
    return {k: v for k, v in meta.items() if k not in forbidden}
