"""Conversation store — in-memory + optional SQLite persistence for Michi Assistant."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import time

from integrations.ai_assistant.schemas import ConversationTurn

logger = logging.getLogger("michi.ai_assistant.conversation_store")

def _default_db_dir() -> str:
    from core.paths import ai_assistant_dir
    return ai_assistant_dir()


def _default_db_path() -> str:
    return os.path.join(_default_db_dir(), "conversations.sqlite")

_DB_PATH = _default_db_path()


class ConversationStore:
    def __init__(self, save_history: bool = False):
        self._turns: list[ConversationTurn] = []
        self._save_history = save_history
        self._conn: sqlite3.Connection | None = None
        if save_history:
            self._init_db()
            self._load_history()

    def _init_db(self):
        try:
            os.makedirs(_default_db_dir(), exist_ok=True)
            self._conn = sqlite3.connect(_DB_PATH)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tool_name TEXT DEFAULT NULL,
                tool_result_json TEXT DEFAULT NULL
            )""")
            self._conn.commit()
        except Exception as e:
            logger.warning("ConversationStore DB init failed: %s", e)
            self._save_history = False
            self._conn = None

    def _load_history(self):
        if not self._conn:
            return
        try:
            rows = self._conn.execute(
                "SELECT role, content, tool_name, tool_result_json "
                "FROM messages ORDER BY id ASC"
            ).fetchall()
            for role, content, tool_name, tool_json in rows:
                tool_result = None
                if tool_json:
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        tool_result = json.loads(tool_json)
                self._turns.append(ConversationTurn(
                    role=role, content=content or "",
                    tool_name=tool_name, tool_result=tool_result,
                ))
        except Exception as e:
            logger.warning("ConversationStore load history failed: %s", e)

    def _persist(self, turn: ConversationTurn):
        if not self._conn:
            return
        try:
            tool_json = None
            if turn.tool_result:
                tool_json = json.dumps(turn.tool_result, ensure_ascii=False)
            self._conn.execute(
                "INSERT INTO messages (timestamp, role, content, tool_name, tool_result_json) "
                "VALUES (?,?,?,?,?)",
                (time.time(), turn.role, turn.content,
                 turn.tool_name, tool_json),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("ConversationStore persist failed: %s", e)

    def add(self, role: str, content: str,
            tool_name: str | None = None, tool_result: dict | None = None):
        turn = ConversationTurn(
            role=role, content=content,
            tool_name=tool_name, tool_result=tool_result,
        )
        self._turns.append(turn)
        if self._save_history:
            self._persist(turn)

    def get_all(self) -> list[ConversationTurn]:
        return list(self._turns)

    def get_for_ollama(self, max_tokens: int = 1800) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        token_estimate = 0
        for turn in reversed(self._turns):
            if turn.role in ("system", "user", "assistant"):
                trigger = turn.role
                if trigger == "system" and messages:
                    continue
                content = turn.content or ""
                estimated = len(content.split()) + len(content) // 4
                if token_estimate + estimated > max_tokens:
                    break
                messages.insert(0, {"role": trigger, "content": content})
                token_estimate += estimated
            if turn.tool_result:
                result_text = str(turn.tool_result)
                estimated = len(result_text.split()) + len(result_text) // 4
                if token_estimate + estimated > max_tokens:
                    break
                token_estimate += estimated
        return messages

    def clear(self):
        self._turns.clear()
        if self._conn:
            try:
                self._conn.execute("DELETE FROM messages")
                self._conn.commit()
            except Exception:
                pass

    def count(self) -> int:
        return len(self._turns)

    @property
    def save_history(self) -> bool:
        return self._save_history
