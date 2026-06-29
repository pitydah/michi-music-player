"""SQLite persistence for the unified job queue."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from typing import Any

from core.jobs.job_types import Job, JobStatus, JobType

logger = logging.getLogger("michi.jobs.persistence")

MIGRATION_SQL = """
CREATE TABLE IF NOT EXISTS job_queue (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0.0,
    label TEXT NOT NULL DEFAULT '',
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    params_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    log_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL DEFAULT '',
    finished_at TEXT NOT NULL DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2,
    cancellable INTEGER NOT NULL DEFAULT 1,
    pausable INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_job_status ON job_queue(status);
CREATE INDEX IF NOT EXISTS idx_job_type ON job_queue(type);
CREATE INDEX IF NOT EXISTS idx_job_entity ON job_queue(entity_type, entity_id);
"""


def _default_db_path() -> str:
    from core.paths import app_data_dir
    return os.path.join(app_data_dir(), "job_queue.db")


class JobRepository:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = _default_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(MIGRATION_SQL)
        self._conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            type=JobType(row["type"]),
            status=JobStatus(row["status"]),
            progress=row["progress"],
            label=row["label"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            params=json.loads(row["params_json"]),
            result=json.loads(row["result_json"]),
            error=row["error"],
            log=json.loads(row["log_json"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            cancellable=bool(row["cancellable"]),
            pausable=bool(row["pausable"]),
        )

    def create_job(self, job: Job) -> str:
        if not job.id:
            job.id = str(uuid.uuid4())[:12]
        if not job.created_at:
            job.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._conn.execute(
            """INSERT OR REPLACE INTO job_queue
            (id, type, status, progress, label, entity_type, entity_id,
             params_json, result_json, error, log_json,
             created_at, started_at, finished_at, retry_count, max_retries,
             cancellable, pausable)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job.id, job.type.value, job.status.value, job.progress,
             job.label, job.entity_type, job.entity_id,
             json.dumps(job.params), json.dumps(job.result),
             job.error, json.dumps(job.log),
             job.created_at, job.started_at, job.finished_at,
             job.retry_count, job.max_retries,
             int(job.cancellable), int(job.pausable)),
        )
        self._conn.commit()
        return job.id

    def update_status(self, job_id: str, status: JobStatus, **extra):
        sets = ["status=?"]
        values: list[Any] = [status.value]
        if status == JobStatus.RUNNING and "started_at" not in extra:
            sets.append("started_at=?")
            values.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED) and "finished_at" not in extra:
                sets.append("finished_at=?")
                values.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
        for k, v in extra.items():
            if k.endswith("_json") and not isinstance(v, str):
                v = json.dumps(v)
            sets.append(f"{k}=?")
            values.append(v)
        values.append(job_id)
        self._conn.execute(
            f"UPDATE job_queue SET {', '.join(sets)} WHERE id=?", values
        )
        self._conn.commit()

    def get_job(self, job_id: str) -> Job | None:
        row = self._conn.execute(
            "SELECT * FROM job_queue WHERE id=?", (job_id,)
        ).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, status: JobStatus | None = None,
                  type_filter: JobType | None = None,
                  limit: int = 100) -> list[Job]:
        parts = ["SELECT * FROM job_queue"]
        params: list[Any] = []
        conds = []
        if status:
            conds.append("status=?")
            params.append(status.value)
        if type_filter:
            conds.append("type=?")
            params.append(type_filter.value)
        if conds:
            parts.append("WHERE " + " AND ".join(conds))
        parts.append("ORDER BY created_at DESC LIMIT ?")
        params.append(limit)
        rows = self._conn.execute(" ".join(parts), params).fetchall()
        return [self._row_to_job(r) for r in rows]

    def pending_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM job_queue WHERE status IN ('pending','running')"
        ).fetchone()
        return row[0] if row else 0

    def delete_job(self, job_id: str):
        self._conn.execute("DELETE FROM job_queue WHERE id=?", (job_id,))
        self._conn.commit()

    def close(self):
        self._conn.close()
