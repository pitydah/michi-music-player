from __future__ import annotations

import datetime
import sqlite3
from typing import Callable

from core.metadata.models import JournalEntry, MetadataOperationResult
from core.metadata.enums import JournalStatus, MetadataErrorCode


class MetadataJournalRepository:
    def __init__(self, db_path: str,
                 clock: Callable[[], str] | None = None):
        self._db_path = db_path
        self._clock = clock or (
            lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    def initialize(self):
        conn = self._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_journal (
                    operation_id TEXT PRIMARY KEY,
                    batch_id TEXT DEFAULT '',
                    target TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'planned',
                    before_signature TEXT DEFAULT '',
                    after_signature TEXT DEFAULT '',
                    patch TEXT DEFAULT '{}',
                    backup_reference TEXT DEFAULT '',
                    started_at TEXT DEFAULT '',
                    completed_at TEXT DEFAULT '',
                    result_code TEXT DEFAULT '',
                    rollback_status TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_batch
                ON metadata_journal(batch_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_status
                ON metadata_journal(status)
            """)
            conn.commit()
        finally:
            conn.close()

    def create(self, entry: JournalEntry) -> MetadataOperationResult:
        conn = self._conn()
        try:
            conn.execute("""
                INSERT INTO metadata_journal
                (operation_id, batch_id, target, status, before_signature,
                 patch, backup_reference, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.operation_id, entry.batch_id, entry.target,
                entry.status.value, entry.before_signature,
                entry.patch, entry.backup_reference, entry.started_at,
            ))
            conn.commit()
            return MetadataOperationResult(ok=True)
        except sqlite3.Error as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.JOURNAL_FAILED.value,
                message=str(e),
            )
        finally:
            conn.close()

    def update_status(self, operation_id: str, status: JournalStatus,
                      after_signature: str = "",
                      result_code: str = ""):
        conn = self._conn()
        try:
            conn.execute("""
                UPDATE metadata_journal SET
                    status = ?,
                    after_signature = ?,
                    completed_at = ?,
                    result_code = ?
                WHERE operation_id = ?
            """, (status.value, after_signature, self._clock(), result_code, operation_id))
            conn.commit()
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    def update_rollback(self, operation_id: str, rollback_status: str):
        conn = self._conn()
        try:
            conn.execute("""
                UPDATE metadata_journal SET rollback_status = ? WHERE operation_id = ?
            """, (rollback_status, operation_id))
            conn.commit()
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    def get(self, operation_id: str) -> JournalEntry | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM metadata_journal WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row is None:
                return None
            return JournalEntry(
                operation_id=row["operation_id"],
                batch_id=row["batch_id"],
                target=row["target"],
                status=JournalStatus(row["status"]),
                before_signature=row["before_signature"],
                after_signature=row["after_signature"],
                patch=row["patch"],
                backup_reference=row["backup_reference"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                result_code=row["result_code"],
                rollback_status=row["rollback_status"],
            )
        finally:
            conn.close()

    def list_by_batch(self, batch_id: str) -> list[JournalEntry]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM metadata_journal WHERE batch_id = ? ORDER BY started_at",
                (batch_id,),
            ).fetchall()
            return [
                JournalEntry(
                    operation_id=r["operation_id"],
                    batch_id=r["batch_id"],
                    target=r["target"],
                    status=JournalStatus(r["status"]),
                    before_signature=r["before_signature"],
                    after_signature=r["after_signature"],
                    patch=r["patch"],
                    backup_reference=r["backup_reference"],
                    started_at=r["started_at"],
                    completed_at=r["completed_at"],
                    result_code=r["result_code"],
                    rollback_status=r["rollback_status"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def list_recent(self, limit: int = 50) -> list[JournalEntry]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM metadata_journal ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [JournalEntry(
                operation_id=r["operation_id"],
                batch_id=r["batch_id"],
                target=r["target"],
                status=JournalStatus(r["status"]),
                before_signature=r["before_signature"],
                after_signature=r["after_signature"],
                patch=r["patch"],
                backup_reference=r["backup_reference"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                result_code=r["result_code"],
                rollback_status=r["rollback_status"],
            ) for r in rows]
        finally:
            conn.close()

    def count_by_status(self, status: JournalStatus) -> int:
        conn = self._conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM metadata_journal WHERE status = ?",
                (status.value,),
            ).fetchone()[0]
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
