"""MixRepository — persistence for mix rules/definitions in SQLite."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("michi.mix.repository")


@dataclass
class MixDefinition:
    mix_id: str = ""
    name: str = ""
    rules_json: str = ""
    limit: int = 30
    sort_by: str = "random"
    seed: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    play_count: int = 0


class MixRepository:
    def __init__(self, db):
        self._db = db
        self._ensure_table()

    def _ensure_table(self):
        self._db.conn.execute("""
            CREATE TABLE IF NOT EXISTS mix_definitions (
                mix_id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                rules_json TEXT NOT NULL DEFAULT '{}',
                limit_count INTEGER NOT NULL DEFAULT 30,
                sort_by TEXT NOT NULL DEFAULT 'random',
                seed INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0,
                play_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._db.conn.commit()

    def save(self, definition: MixDefinition) -> dict:
        now = time.time()
        self._db.conn.execute("""
            INSERT OR REPLACE INTO mix_definitions
            (mix_id, name, rules_json, limit_count, sort_by, seed, created_at, updated_at, play_count)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM mix_definitions WHERE mix_id=?), ?), ?, ?)
        """, (
            definition.mix_id, definition.name, definition.rules_json,
            definition.limit, definition.sort_by, definition.seed,
            definition.mix_id, now, now, definition.play_count,
        ))
        self._db.conn.commit()
        return {"ok": True, "mix_id": definition.mix_id}

    def load(self, mix_id: str) -> MixDefinition | None:
        row = self._db.conn.execute(
            "SELECT mix_id, name, rules_json, limit_count, sort_by, seed, created_at, updated_at, play_count "
            "FROM mix_definitions WHERE mix_id=?", (mix_id,)
        ).fetchone()
        if not row:
            return None
        return MixDefinition(
            mix_id=row[0], name=row[1], rules_json=row[2],
            limit=row[3], sort_by=row[4], seed=row[5],
            created_at=row[6], updated_at=row[7], play_count=row[8],
        )

    def list_all(self) -> list[MixDefinition]:
        rows = self._db.conn.execute(
            "SELECT mix_id, name, rules_json, limit_count, sort_by, seed, created_at, updated_at, play_count "
            "FROM mix_definitions ORDER BY updated_at DESC"
        ).fetchall()
        return [MixDefinition(mix_id=r[0], name=r[1], rules_json=r[2],
                              limit=r[3], sort_by=r[4], seed=r[5],
                              created_at=r[6], updated_at=r[7], play_count=r[8])
                for r in rows]

    def delete(self, mix_id: str) -> dict:
        self._db.conn.execute("DELETE FROM mix_definitions WHERE mix_id=?", (mix_id,))
        self._db.conn.commit()
        return {"ok": True}

    def record_play(self, mix_id: str) -> dict:
        self._db.conn.execute(
            "UPDATE mix_definitions SET play_count = play_count + 1 WHERE mix_id=?", (mix_id,)
        )
        self._db.conn.commit()
        return {"ok": True}
