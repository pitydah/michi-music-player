from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from michi_ai.v2.core.models import (
    AssistantSession, ConversationTurn, ErrorCode, OperationResult,
)

logger = logging.getLogger(__name__)


class PersistenceMode:
    MEMORY_ONLY = "MEMORY_ONLY"
    LOCAL_EPHEMERAL = "LOCAL_EPHEMERAL"
    LOCAL_PERSISTENT = "LOCAL_PERSISTENT"


class ConversationService:
    MAX_TURNS_DEFAULT = 100
    MAX_TOKENS_ESTIMATE = 4096

    def __init__(self, persistence_mode: str = PersistenceMode.LOCAL_EPHEMERAL, db_path: str = "", max_turns: int = MAX_TURNS_DEFAULT) -> None:
        self._persistence_mode = persistence_mode
        self._db_path = db_path
        self._max_turns = max_turns
        self._sessions: dict[str, AssistantSession] = {}
        self._db_conn: sqlite3.Connection | None = None
        self._initialized = False

        if persistence_mode != PersistenceMode.MEMORY_ONLY:
            self._init_db()

    def _init_db(self) -> None:
        if not self._db_path:
            data_dir = os.environ.get("MICHI_DATA_DIR", os.path.expanduser("~/.local/share/michi"))
            os.makedirs(data_dir, exist_ok=True)
            self._db_path = os.path.join(data_dir, "ai_conversations.db")

        try:
            self._db_conn = sqlite3.connect(self._db_path, timeout=3)
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA synchronous=NORMAL")
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_name TEXT DEFAULT '',
                    tool_args TEXT DEFAULT '{}',
                    tool_result TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            self._db_conn.commit()
            self._initialized = True
        except Exception as e:
            logger.warning("Failed to init conversation DB: %s. Falling back to memory.", e)
            self._persistence_mode = PersistenceMode.MEMORY_ONLY

    def create_session(self, metadata: dict[str, Any] | None = None) -> OperationResult[AssistantSession]:
        session_id = uuid.uuid4().hex[:16]
        now = datetime.now(timezone.utc)
        session = AssistantSession(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session

        if self._persist():
            self._save_session_to_db(session)

        return OperationResult.success(data=session, message="Session created")

    def get_session(self, session_id: str) -> OperationResult[AssistantSession]:
        session = self._sessions.get(session_id)
        if session is None:
            if self._persist():
                session = self._load_session_from_db(session_id)
            if session is None:
                return OperationResult.failure(ErrorCode.SESSION_NOT_FOUND, f"Session '{session_id}' not found")
        return OperationResult.success(data=session)

    def add_turn(self, session_id: str, turn: ConversationTurn) -> OperationResult[AssistantSession]:
        session_result = self.get_session(session_id)
        if not session_result.ok or session_result.data is None:
            return OperationResult.failure(ErrorCode.SESSION_NOT_FOUND, "Session not found")

        session = session_result.data
        session.turns.append(turn)
        session.updated_at = datetime.now(timezone.utc)

        if len(session.turns) > self._max_turns:
            session.turns = session.turns[-self._max_turns:]

        if self._persist():
            self._save_turn_to_db(session_id, turn)
            self._update_session_db(session)

        return OperationResult.success(data=session)

    def get_history(self, session_id: str, limit: int = 20) -> OperationResult[list[ConversationTurn]]:
        session_result = self.get_session(session_id)
        if not session_result.ok or session_result.data is None:
            return OperationResult.failure(ErrorCode.SESSION_NOT_FOUND, "Session not found")
        turns = session_result.data.turns[-limit:] if limit else session_result.data.turns
        return OperationResult.success(data=turns)

    def clear_history(self, session_id: str) -> OperationResult[None]:
        session_result = self.get_session(session_id)
        if not session_result.ok:
            return session_result
        session_result.data.turns.clear()
        session_result.data.updated_at = datetime.now(timezone.utc)

        if self._persist():
            try:
                c = self._db_conn.cursor()
                c.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
                self._db_conn.commit()
            except Exception as e:
                logger.debug("DB clear error: %s", e)
        return OperationResult.success()

    def delete_session(self, session_id: str) -> OperationResult[None]:
        self._sessions.pop(session_id, None)
        if self._persist():
            try:
                c = self._db_conn.cursor()
                c.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
                c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                self._db_conn.commit()
            except Exception as e:
                logger.debug("DB delete error: %s", e)
        return OperationResult.success()

    def get_context_messages(self, session_id: str, max_tokens: int = MAX_TOKENS_ESTIMATE) -> list[dict[str, str]]:
        session_result = self.get_session(session_id)
        if not session_result.ok or session_result.data is None:
            return []
        messages: list[dict[str, str]] = []
        total = 0
        for turn in reversed(session_result.data.turns):
            content = self._truncate_for_token_estimate(turn.content, max_tokens - total)
            if not content:
                break
            msg = {"role": turn.role, "content": content}
            messages.insert(0, msg)
            total += len(content) // 4
        return messages

    def list_sessions(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if self._persist() and self._db_conn:
            try:
                c = self._db_conn.cursor()
                c.execute("SELECT session_id, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 50")
                for row in c.fetchall():
                    result.append({"session_id": row[0], "created_at": row[1], "updated_at": row[2]})
            except Exception:
                pass
        for sid, session in self._sessions.items():
            if not any(s.get("session_id") == sid for s in result):
                result.append({
                    "session_id": sid,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                })
        return result

    def get_pending_plan(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session and session.pending_plan:
            return {"plan_id": session.pending_plan} if isinstance(session.pending_plan, str) else session.pending_plan
        return None

    def set_pending_plan(self, session_id: str, plan_data: Any) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.pending_plan = plan_data

    def clear_pending_plan(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.pending_plan = None

    def _persist(self) -> bool:
        return self._persistence_mode != PersistenceMode.MEMORY_ONLY and self._db_conn is not None

    def _save_session_to_db(self, session: AssistantSession) -> None:
        try:
            c = self._db_conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO sessions (session_id, created_at, updated_at, metadata) VALUES (?, ?, ?, ?)",
                (session.session_id, session.created_at.isoformat(), session.updated_at.isoformat(),
                 json.dumps(session.metadata)),
            )
            self._db_conn.commit()
        except Exception as e:
            logger.debug("DB save session error: %s", e)

    def _save_turn_to_db(self, session_id: str, turn: ConversationTurn) -> None:
        try:
            c = self._db_conn.cursor()
            c.execute(
                "INSERT INTO turns (session_id, role, content, timestamp, tool_name, tool_args, tool_result) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, turn.role, turn.content, turn.timestamp.isoformat(),
                 turn.tool_name, json.dumps(turn.tool_args),
                 json.dumps(turn.tool_result) if turn.tool_result else None),
            )
            self._db_conn.commit()
        except Exception as e:
            logger.debug("DB save turn error: %s", e)

    def _update_session_db(self, session: AssistantSession) -> None:
        try:
            c = self._db_conn.cursor()
            c.execute(
                "UPDATE sessions SET updated_at = ?, metadata = ? WHERE session_id = ?",
                (session.updated_at.isoformat(), json.dumps(session.metadata), session.session_id),
            )
            self._db_conn.commit()
        except Exception as e:
            logger.debug("DB update session error: %s", e)

    def _load_session_from_db(self, session_id: str) -> AssistantSession | None:
        try:
            c = self._db_conn.cursor()
            c.execute("SELECT session_id, created_at, updated_at, metadata FROM sessions WHERE session_id = ?", (session_id,))
            row = c.fetchone()
            if row is None:
                return None
            metadata = json.loads(row[3]) if row[3] else {}
            session = AssistantSession(
                session_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                metadata=metadata,
            )
            c.execute("SELECT role, content, timestamp, tool_name, tool_args, tool_result FROM turns WHERE session_id = ? ORDER BY id ASC", (session_id,))
            for turn_row in c.fetchall():
                turn = ConversationTurn(
                    role=turn_row[0],
                    content=turn_row[1],
                    timestamp=datetime.fromisoformat(turn_row[2]),
                    tool_name=turn_row[3] or "",
                    tool_args=json.loads(turn_row[4]) if turn_row[4] else {},
                    tool_result=json.loads(turn_row[5]) if turn_row[5] else None,
                )
                session.turns.append(turn)
            self._sessions[session_id] = session
            return session
        except Exception as e:
            logger.debug("DB load session error: %s", e)
            return None

    def _truncate_for_token_estimate(self, text: str, max_chars: int) -> str:
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
