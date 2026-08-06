"""JobService — durable job management with rich state machine.

Contract: id, type, owner, state, createdAt, startedAt, finishedAt,
          progress, current, total, message, warnings, errors,
          cancellable, pausable, retryable, payload, result, processId.

States: QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED,
        SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED.

Execution: when a WorkerManager is injected the handler runs on its
thread pool (real async execution, cooperative cancellation via the
TaskContext passed to the handler); without one the handler runs
inline on the caller thread (backward-compatible synchronous path).

Handler contract: ``handler(job, ctx)`` where ``ctx`` exposes
``raise_if_cancelled()``, ``report_progress(percent, message)`` and
``progress_cb(current, total, message)`` (legacy alias).

On restart, RUNNING -> INTERRUPTED and QUEUED jobs are re-enqueued.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from core.worker_manager import CancellationToken, TaskContext

logger = logging.getLogger("michi.jobs.durable")


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


TERMINAL_STATES = {
    JobState.CANCELLED, JobState.SUCCEEDED,
    JobState.PARTIAL_SUCCESS, JobState.FAILED, JobState.INTERRUPTED,
}


@dataclass
class DurableJob:
    id: str = ""
    type: str = ""
    owner: str = ""
    state: JobState = JobState.QUEUED
    createdAt: str = ""
    startedAt: str = ""
    finishedAt: str = ""
    progress: float = 0.0
    current: int = 0
    total: int = 0
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    cancellable: bool = True
    pausable: bool = True
    retryable: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    processId: str = ""


class _SyncContext:
    """TaskContext-compatible object for the synchronous (no-WM) path.

    Exposes the same cooperative-cancellation and progress surface that
    handlers receive in the asynchronous path, backed by a thread-local
    CancellationToken requested by ``cancel_job``.
    """

    def __init__(self, service: "DurableJobService", job_id: str):
        self.job_id = job_id
        self.task_id = f"job_{job_id}"
        self.owner = "jobs"
        self.token = CancellationToken()
        self._service = service

    def raise_if_cancelled(self):
        self.token.raise_if_cancelled()

    def report_progress(self, percent: float, message: str = ""):
        self._service._apply_progress(self.job_id, percent, message or "")

    def progress_cb(self, current: int, total: int, message: str = ""):
        self._service.update_progress(self.job_id, current, total, message or "")


class DurableJobService(QObject):
    jobCreated = Signal(str)
    jobStarted = Signal(str)
    jobProgress = Signal(str, float)
    jobPaused = Signal(str)
    jobResumed = Signal(str)
    jobCancelled = Signal(str)
    jobCompleted = Signal(str, object)
    jobFailed = Signal(str, str)
    queueChanged = Signal(int)

    def __init__(self, db_path: str | None = None, worker_manager=None,
                 parent=None):
        super().__init__(parent)
        self._jobs: dict[str, DurableJob] = {}
        self._handlers: dict[str, Callable] = {}
        self._max_concurrent = 4
        self._active: set[str] = set()
        self._tokens: dict[str, CancellationToken] = {}
        self._db_path = db_path or self._default_db_path()
        self._wm = worker_manager
        self._restore_running_jobs()

    def _default_db_path(self) -> str:
        from core.paths import app_data_dir
        return os.path.join(app_data_dir(), "durable_jobs.db")

    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    def _job_id(self) -> str:
        return str(uuid.uuid4())[:12]

    def _restore_running_jobs(self):
        """Restore non-terminal rows from the previous process.

        RUNNING -> INTERRUPTED (persisted AND visible in the live registry,
        so a recovered job is always retryable). QUEUED/PAUSED jobs are
        reloaded into memory (QUEUED resumes via ``resume_pending_jobs``
        once handlers are registered; PAUSED stays paused but visible).
        CANCELLING rows are finalized as CANCELLED without loading
        (terminal rows are never part of the live registry).
        """
        running = self._load_by_state(JobState.RUNNING)
        for job in running:
            job.state = JobState.INTERRUPTED
            job.finishedAt = self._now()
            job.message = "Interrumpido por reinicio"
            self._save_job(job)
            logger.info("Job %s marked INTERRUPTED on restart", job.id)
        pausing = self._load_by_state(JobState.PAUSING)
        for job in pausing:
            job.state = JobState.PAUSED
            job.message = "En pausa (recuperado)"
            self._save_job(job)
            logger.info("Job %s marked PAUSED on restart", job.id)
        for state in (JobState.QUEUED, JobState.PAUSED):
            for job in self._load_by_state(state):
                self._jobs[job.id] = job
                logger.info("Job %s restored %s on restart", job.id, state.value)
        cancelling = self._load_by_state(JobState.CANCELLING)
        for job in cancelling:
            job.state = JobState.CANCELLED
            job.finishedAt = self._now()
            job.message = "Cancelado antes del reinicio"
            self._persist_job(job)
            logger.info("Job %s marked CANCELLED on restart", job.id)

    def resume_pending_jobs(self, max_jobs: int = 2) -> dict[str, int]:
        """Boot recovery: process QUEUED jobs once handlers are registered.

        MUST be called after ``register_handler`` for every kind the app
        supports (composition does this at the end of boot). A QUEUED job
        whose kind has no handler is marked FAILED with a persisted
        ``HANDLER_UNAVAILABLE`` error so it never lingers silently. The rest
        are started through ``process_queue`` with the given capacity limit.

        Idempotent: a second call finds no QUEUED jobs left.
        """
        stats = {"queued": 0, "resumed": 0, "handler_unavailable": 0}
        for job_id, job in list(self._jobs.items()):
            if job.state != JobState.QUEUED:
                continue
            stats["queued"] += 1
            if job.type not in self._handlers:
                self._fail_job(job_id, f"HANDLER_UNAVAILABLE: {job.type}")
                stats["handler_unavailable"] += 1
        stats["resumed"] = self.process_queue(max_jobs=max_jobs)
        return stats

    def register_handler(self, job_type: str, handler: Callable):
        self._handlers[job_type] = handler

    def create_job(self, job_type: str, owner: str = "",
                   payload: dict[str, Any] | None = None,
                   total: int = 0,
                   cancellable: bool = True,
                   pausable: bool = True,
                   retryable: bool = True) -> str:
        job = DurableJob(
            id=self._job_id(),
            type=job_type,
            owner=owner,
            state=JobState.QUEUED,
            createdAt=self._now(),
            total=total,
            cancellable=cancellable,
            pausable=pausable,
            retryable=retryable,
            payload=payload or {},
        )
        self._jobs[job.id] = job
        self._save_job(job)
        self.jobCreated.emit(job.id)
        self.queueChanged.emit(len([j for j in self._jobs.values() if j.state == JobState.QUEUED]))
        return job.id

    def start_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.state != JobState.QUEUED:
            return False
        if len(self._active) >= self._max_concurrent:
            return False
        handler = self._handlers.get(job.type)
        if not handler:
            self._fail_job(job_id, f"No handler for type: {job.type}")
            return False
        job.state = JobState.RUNNING
        job.startedAt = self._now()
        self._active.add(job_id)
        self._save_job(job)
        self.jobStarted.emit(job_id)
        self.queueChanged.emit(self._queue_count())
        if self._wm is not None:
            self._submit_async(job, handler)
        else:
            self._execute_handler(job, handler)
        return True

    # ── Async execution (WorkerManager) ──

    def _submit_async(self, job: DurableJob, handler: Callable):
        task_id = f"job_{job.id}"

        def run(ctx: TaskContext):
            ctx.job_id = job.id
            ctx.token.raise_if_cancelled()
            return handler(job, ctx)

        def on_done(result):
            if self._jobs.get(job.id) is not job:
                return
            self._active.discard(job.id)
            self._finalize_handler_result(job, result)
            self.queueChanged.emit(self._queue_count())
            self._drain_queue()

        def on_error(code: str, message: str):
            if self._jobs.get(job.id) is not job:
                return
            self._active.discard(job.id)
            self._fail_job(job.id, message or code)
            self._drain_queue()

        def on_cancelled():
            if self._jobs.get(job.id) is not job:
                return
            self._active.discard(job.id)
            current = self._jobs.get(job.id)
            if current and current.state == JobState.CANCELLING:
                current.state = JobState.CANCELLED
                current.finishedAt = self._now()
                current.message = "Cancelado por el usuario"
                self._save_job(current)
                self.jobCancelled.emit(current.id)
            self.queueChanged.emit(self._queue_count())
            self._drain_queue()

        def on_progress(percent: float, message: str):
            self._apply_progress(job.id, float(percent), message or "")

        self._wm.run_task(
            task_id, run,
            owner=job.owner or "jobs",
            cancellable=job.cancellable,
            pass_context=True,
            on_done=on_done,
            on_error=on_error,
            on_cancelled=on_cancelled,
            on_progress=on_progress,
        )

    def _execute_handler(self, job: DurableJob, handler: Callable):
        ctx = _SyncContext(self, job.id)
        self._tokens[job.id] = ctx.token
        try:
            result = handler(job, ctx)
            self._finalize_handler_result(job, result)
        except Exception as e:
            logger.exception("Job %s handler failed", job.id)
            self._fail_job(job.id, str(e))
        finally:
            self._tokens.pop(job.id, None)
            self._active.discard(job.id)
            self.queueChanged.emit(self._queue_count())

    def _finalize_handler_result(self, job: DurableJob, result):
        if job.state == JobState.CANCELLING:
            job.state = JobState.CANCELLED
            job.finishedAt = self._now()
            job.message = "Cancelado por el usuario"
            self._save_job(job)
            self.jobCancelled.emit(job.id)
        elif isinstance(result, dict) and result.get("partial"):
            job.state = JobState.PARTIAL_SUCCESS
            job.result = result
            job.finishedAt = self._now()
            self._save_job(job)
            self.jobCompleted.emit(job.id, result)
        else:
            job.state = JobState.SUCCEEDED
            job.progress = 1.0
            job.current = job.total
            job.result = result if isinstance(result, dict) else {}
            job.finishedAt = self._now()
            self._save_job(job)
            self.jobCompleted.emit(job.id, job.result)

    def pause_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or not job.pausable or job.state not in (JobState.RUNNING, JobState.QUEUED):
            return False
        job.state = JobState.PAUSED
        job.message = "En pausa"
        self._save_job(job)
        self._active.discard(job_id)
        self.jobPaused.emit(job_id)
        self.queueChanged.emit(self._queue_count())
        return True

    def resume_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.state != JobState.PAUSED:
            return False
        job.state = JobState.QUEUED
        job.message = "Reanudado"
        self._save_job(job)
        self.jobResumed.emit(job_id)
        self.queueChanged.emit(self._queue_count())
        return True

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.state in TERMINAL_STATES:
            return False
        if job.state == JobState.RUNNING:
            job.state = JobState.CANCELLING
            self._save_job(job)
            self.jobCancelled.emit(job_id)
            if self._wm is not None and job.cancellable:
                self._wm.cancel_task(f"job_{job_id}")
            elif self._wm is None:
                token = self._tokens.get(job_id)
                if token is not None:
                    token.request_cancel()
        else:
            job.state = JobState.CANCELLED
            job.finishedAt = self._now()
            job.message = "Cancelado"
            self._save_job(job)
            self._active.discard(job_id)
            self.jobCancelled.emit(job_id)
        self.queueChanged.emit(self._queue_count())
        return True

    def retry_job(self, job_id: str) -> bool:
        """Re-queue a terminal job with its ORIGINAL payload and start it.

        Unified retry entry point (ADR-004, Fase Jobs): JobBridge.retryJob
        and NotificationActionService.retry both go through this method.
        Validates the state (only FAILED/INTERRUPTED/CANCELLED are
        retryable), preserves the payload, transitions to QUEUED, persists,
        emits, then starts immediately when capacity allows. Callers read
        back the real state via ``get_job``.
        """
        job = self._jobs.get(job_id)
        if not job or not job.retryable or job.state not in (
            JobState.FAILED, JobState.INTERRUPTED, JobState.CANCELLED
        ):
            return False
        job.state = JobState.QUEUED
        job.progress = 0.0
        job.current = 0
        job.errors = []
        job.warnings = []
        job.message = ""
        job.finishedAt = ""
        self._save_job(job)
        self.queueChanged.emit(self._queue_count())
        self.start_job(job_id)
        return True

    def update_progress(self, job_id: str, current: int, total: int, message: str = ""):
        job = self._jobs.get(job_id)
        if not job:
            return
        job.current = current
        job.total = total
        job.progress = current / total if total > 0 else 0.0
        job.message = message
        self._save_job(job)
        self.jobProgress.emit(job_id, job.progress)

    def _apply_progress(self, job_id: str, fraction: float, message: str = ""):
        job = self._jobs.get(job_id)
        if not job:
            return
        fraction = max(0.0, min(1.0, float(fraction)))
        if job.total > 0:
            self.update_progress(job_id, int(fraction * job.total), job.total, message)
        else:
            job.progress = max(job.progress, fraction)
            job.message = message
            self._save_job(job)
            self.jobProgress.emit(job_id, job.progress)

    def add_warning(self, job_id: str, warning: str):
        job = self._jobs.get(job_id)
        if job:
            job.warnings.append(warning)
            self._save_job(job)

    def add_error(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if job:
            job.errors.append(error)
            self._save_job(job)

    def get_job(self, job_id: str) -> DurableJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self, state: JobState | None = None,
                  job_type: str | None = None,
                  owner: str | None = None,
                  limit: int = 100) -> list[dict[str, Any]]:
        matches = list(self._jobs.values())
        if state:
            matches = [j for j in matches if j.state == state]
        if job_type:
            matches = [j for j in matches if j.type == job_type]
        if owner:
            matches = [j for j in matches if j.owner == owner]
        matches.sort(key=lambda j: j.createdAt, reverse=True)
        return [self._job_to_dict(j) for j in matches[:limit]]

    def _queue_count(self) -> int:
        return len([j for j in self._jobs.values() if j.state == JobState.QUEUED])

    def process_queue(self, max_jobs: int = 2):
        started = 0
        for job_id, job in list(self._jobs.items()):
            if len(self._active) >= self._max_concurrent:
                break
            if started >= max_jobs:
                break
            if job.state == JobState.QUEUED and self.start_job(job_id):
                started += 1
        return started

    def _drain_queue(self):
        """Start queued jobs when a running job frees capacity."""
        if self._active:
            self.process_queue()

    def cancel_all(self):
        for job_id in list(self._jobs.keys()):
            self.cancel_job(job_id)

    def cancel_owner(self, owner: str) -> int:
        """Cancel every job owned by *owner* (never jobs of other domains)."""
        if not owner:
            return 0
        return sum(
            1
            for job_id in list(self._jobs)
            if self._jobs[job_id].owner == owner
            and self.cancel_job(job_id)
        )

    def cancel_scope(self, owner: str, kind: str) -> int:
        """Cancel jobs of one kind owned by *owner* (never jobs of others)."""
        if not owner or not kind:
            return 0
        return sum(
            1
            for job_id in list(self._jobs)
            if self._jobs[job_id].owner == owner
            and self._jobs[job_id].type == kind
            and self.cancel_job(job_id)
        )

    def delete_job(self, job_id: str) -> bool:
        """Remove a terminal job from memory and from the durable store."""
        job = self._jobs.get(job_id)
        if not job or job.state not in TERMINAL_STATES:
            return False
        del self._jobs[job_id]
        self._delete_persisted_job(job_id)
        self.queueChanged.emit(self._queue_count())
        return True

    def _fail_job(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if not job:
            return
        job.state = JobState.FAILED
        job.errors.append(error)
        job.message = error
        job.finishedAt = self._now()
        self._save_job(job)
        self._active.discard(job_id)
        self.jobFailed.emit(job_id, error)
        self.queueChanged.emit(self._queue_count())

    def _save_job(self, job: DurableJob):
        self._jobs[job.id] = job
        self._persist_job(job)

    def _connect(self):
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def _ensure_dir(db_path: str):
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _persist_job(self, job: DurableJob):
        try:
            self._ensure_dir(self._db_path)
            conn = self._connect()
            conn.execute(
                """CREATE TABLE IF NOT EXISTS durable_jobs (
                    id TEXT PRIMARY KEY, type TEXT, owner TEXT, state TEXT,
                    created_at TEXT, started_at TEXT, finished_at TEXT,
                    progress REAL, current INTEGER, total INTEGER,
                    message TEXT, warnings TEXT, errors TEXT,
                    cancellable INTEGER, pausable INTEGER, retryable INTEGER,
                    payload TEXT, result TEXT, process_id TEXT
                )"""
            )
            conn.execute(
                """INSERT OR REPLACE INTO durable_jobs
                (id, type, owner, state, created_at, started_at, finished_at,
                 progress, current, total, message, warnings, errors,
                 cancellable, pausable, retryable, payload, result, process_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    job.id, job.type, job.owner, job.state.value,
                    job.createdAt, job.startedAt, job.finishedAt,
                    job.progress, job.current, job.total, job.message,
                    json.dumps(job.warnings), json.dumps(job.errors),
                    int(job.cancellable), int(job.pausable), int(job.retryable),
                    json.dumps(job.payload), json.dumps(job.result), job.processId,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to persist job %s: %s", job.id, e)

    def _delete_persisted_job(self, job_id: str):
        try:
            self._ensure_dir(self._db_path)
            conn = self._connect()
            conn.execute("DELETE FROM durable_jobs WHERE id=?", (job_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to delete job %s: %s", job_id, e)

    def _load_by_state(self, state: JobState) -> list[DurableJob]:
        jobs = []
        try:
            self._ensure_dir(self._db_path)
            conn = self._connect()
            conn.execute(
                """CREATE TABLE IF NOT EXISTS durable_jobs (
                    id TEXT PRIMARY KEY, type TEXT, owner TEXT, state TEXT,
                    created_at TEXT, started_at TEXT, finished_at TEXT,
                    progress REAL, current INTEGER, total INTEGER,
                    message TEXT, warnings TEXT, errors TEXT,
                    cancellable INTEGER, pausable INTEGER, retryable INTEGER,
                    payload TEXT, result TEXT, process_id TEXT
                )"""
            )
            rows = conn.execute(
                "SELECT * FROM durable_jobs WHERE state=?", (state.value,)
            ).fetchall()
            for row in rows:
                jobs.append(self._row_to_job(row))
            conn.close()
        except Exception as e:
            logger.error("Failed to load jobs by state %s: %s", state, e)
        return jobs

    def _row_to_job(self, row) -> DurableJob:
        return DurableJob(
            id=row[0], type=row[1], owner=row[2], state=JobState(row[3]),
            createdAt=row[4] or "", startedAt=row[5] or "", finishedAt=row[6] or "",
            progress=row[7] or 0.0, current=row[8] or 0, total=row[9] or 0,
            message=row[10] or "",
            warnings=json.loads(row[11]) if row[11] else [],
            errors=json.loads(row[12]) if row[12] else [],
            cancellable=bool(row[13]), pausable=bool(row[14]), retryable=bool(row[15]),
            payload=json.loads(row[16]) if row[16] else {},
            result=json.loads(row[17]) if row[17] else {},
            processId=row[18] or "",
        )

    def _job_to_dict(self, job: DurableJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "type": job.type,
            "owner": job.owner,
            "state": job.state.value,
            "createdAt": job.createdAt,
            "startedAt": job.startedAt,
            "finishedAt": job.finishedAt,
            "progress": job.progress,
            "current": job.current,
            "total": job.total,
            "message": job.message,
            "warnings": list(job.warnings),
            "errors": list(job.errors),
            "cancellable": job.cancellable,
            "pausable": job.pausable,
            "retryable": job.retryable,
            "payload": dict(job.payload),
            "result": dict(job.result),
            "processId": job.processId,
        }

    def cleanup_old_jobs(self, max_age_days: int = 7):
        cutoff = time.time() - max_age_days * 86400
        for job_id, job in list(self._jobs.items()):
            if job.state in TERMINAL_STATES and job.finishedAt:
                try:
                    ft = time.mktime(time.strptime(job.finishedAt, "%Y-%m-%dT%H:%M:%S"))
                    if ft < cutoff:
                        self.delete_job(job_id)
                except (ValueError, OSError):
                    pass
