from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import timedelta
from datetime import datetime, timezone
from typing import Any

from michi_ai.v2.core.models import AssistantTrace

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "token", "password", "api_key", "secret", "cookie", "credentials",
    "auth", "authorization", "bearer", "jwt",
})


class TraceRecorder:
    def __init__(self, db_path: str = "") -> None:
        self._db_path = db_path or os.environ.get(
            "MICHI_TRACE_PATH",
            os.path.expanduser("~/.local/share/michi/ai_traces.db"),
        )
        self._conn: sqlite3.Connection | None = None
        self._initialized = False
        self._init_db()

    def _init_db(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, timeout=3)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    request_id TEXT,
                    intent TEXT,
                    provider TEXT,
                    plan_id TEXT,
                    timestamp TEXT NOT NULL,
                    duration_ms REAL DEFAULT 0,
                    tools TEXT DEFAULT '[]',
                    result_codes TEXT DEFAULT '[]',
                    fallbacks TEXT DEFAULT '[]',
                    cancellations TEXT DEFAULT '[]'
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trace_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT DEFAULT '{}',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
                )
            """)
            self._conn.commit()
            self._initialized = True
        except Exception as e:
            logger.warning("Failed to init trace DB: %s", e)

    def record(self, trace: AssistantTrace) -> None:
        if not self._initialized or self._conn is None:
            return
        try:
            c = self._conn.cursor()
            c.execute(
                """INSERT INTO traces
                   (trace_id, session_id, request_id, intent, provider, plan_id,
                    timestamp, duration_ms, tools, result_codes, fallbacks, cancellations)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trace.trace_id, trace.session_id, trace.request_id,
                    trace.intent, trace.provider, trace.plan_id,
                    trace.timestamp or datetime.now(timezone.utc).isoformat(),
                    trace.durations.get("total", 0),
                    json.dumps(list(trace.tools)),
                    json.dumps(list(trace.result_codes)),
                    json.dumps(list(trace.fallbacks)),
                    json.dumps(list(trace.cancellations)),
                ),
            )
            self._conn.commit()
        except Exception as e:
            logger.debug("Failed to record trace: %s", e)

    def record_event(self, trace_id: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if not self._initialized or self._conn is None:
            return
        try:
            safe_payload = self._sanitize_payload(payload or {})
            c = self._conn.cursor()
            c.execute(
                "INSERT INTO trace_events (trace_id, event_type, payload, timestamp) VALUES (?, ?, ?, ?)",
                (trace_id, event_type, json.dumps(safe_payload), datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()
        except Exception as e:
            logger.debug("Failed to record trace event: %s", e)

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        if not self._initialized or self._conn is None:
            return None
        try:
            c = self._conn.cursor()
            c.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,))
            row = c.fetchone()
            if row is None:
                return None
            return {
                "trace_id": row[0], "session_id": row[1], "request_id": row[2],
                "intent": row[3], "provider": row[4], "plan_id": row[5],
                "timestamp": row[6], "duration_ms": row[7],
                "tools": json.loads(row[8]) if row[8] else [],
                "result_codes": json.loads(row[9]) if row[9] else [],
                "fallbacks": json.loads(row[10]) if row[10] else [],
                "cancellations": json.loads(row[11]) if row[11] else [],
            }
        except Exception as e:
            logger.debug("Failed to get trace: %s", e)
            return None

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._initialized or self._conn is None:
            return []
        try:
            c = self._conn.cursor()
            c.execute("SELECT * FROM traces ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = c.fetchall()
            result = []
            for row in rows:
                result.append({
                    "trace_id": row[0], "session_id": row[1], "request_id": row[2],
                    "intent": row[3], "provider": row[4], "plan_id": row[5],
                    "timestamp": row[6], "duration_ms": row[7],
                    "tools": json.loads(row[8]) if row[8] else [],
                    "result_codes": json.loads(row[9]) if row[9] else [],
                    "fallbacks": json.loads(row[10]) if row[10] else [],
                    "cancellations": json.loads(row[11]) if row[11] else [],
                })
            return result
        except Exception as e:
            logger.debug("Failed to get recent traces: %s", e)
            return []

    def export_sanitized(self, limit: int = 100) -> list[dict[str, Any]]:
        traces = self.get_recent(limit)
        sanitized = []
        for t in traces:
            t.pop("request_id", None)
            t.pop("session_id", None)
            sanitized.append(t)
        return sanitized

    def cleanup_old(self, max_age_days: int = 30) -> int:
        if not self._initialized or self._conn is None:
            return 0
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
            c = self._conn.cursor()
            c.execute("DELETE FROM traces WHERE timestamp < ?", (cutoff,))
            deleted = c.rowcount
            c.execute("DELETE FROM trace_events WHERE timestamp < ?", (cutoff,))
            self._conn.commit()
            return deleted
        except Exception as e:
            logger.debug("Cleanup error: %s", e)
            return 0

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in payload.items() if k.lower() not in _SENSITIVE_KEYS}

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
