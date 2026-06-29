"""Unified job manager — queue, progress, cancellation, persistence.

Wraps WorkerManager (QThreadPool) with a persistent SQLite queue.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from PySide6.QtCore import QObject, Signal

from core.jobs.job_types import Job, JobStatus, JobType
from core.jobs.job_persistence import JobRepository

logger = logging.getLogger("michi.jobs.manager")


class JobManager(QObject):
    job_created = Signal(str)  # job_id
    job_started = Signal(str)
    job_progress = Signal(str, float)  # job_id, progress (0..1)
    job_completed = Signal(str, object)  # job_id, result dict
    job_failed = Signal(str, str)  # job_id, error
    job_cancelled = Signal(str)
    queue_count_changed = Signal(int)

    def __init__(self, worker_mgr=None, parent=None):
        super().__init__(parent)
        self._repo = JobRepository()
        self._worker_mgr = worker_mgr
        self._active: dict[str, Job] = {}
        self._handlers: dict[JobType, Callable] = {}
        self._max_concurrent = 4

    @property
    def pending_count(self) -> int:
        return self._repo.pending_count()

    # ── Handler registration ──

    def register_handler(self, job_type: JobType, handler: Callable):
        """Register a callable that processes one job.

        The handler receives (job, progress_cb) and should call
        progress_cb(value) with 0..1 floats.
        """
        self._handlers[job_type] = handler

    # ── Job lifecycle ──

    def create_job(self, job: Job) -> str:
        job_id = self._repo.create_job(job)
        self.job_created.emit(job_id)
        self.queue_count_changed.emit(self.pending_count)
        return job_id

    def start_job(self, job_id: str) -> bool:
        job = self._repo.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        if len(self._active) >= self._max_concurrent:
            return False

        handler = self._handlers.get(job.type)
        if not handler:
            self._fail_job(job_id, f"No handler for job type: {job.type.value}")
            return False

        self._active[job_id] = job
        self._repo.update_status(job_id, JobStatus.RUNNING)
        self.job_started.emit(job_id)
        self.queue_count_changed.emit(self.pending_count)

        def progress_cb(value: float):
            self._repo.update_status(job_id, JobStatus.RUNNING, progress=value)
            self.job_progress.emit(job_id, value)

        def _run():
            try:
                result = handler(job, progress_cb)
                self._complete_job(job_id, result)
            except Exception as e:
                logger.exception("Job %s failed: %s", job_id, e)
                self._fail_job(job_id, str(e))

        if self._worker_mgr and hasattr(self._worker_mgr, 'run_task'):
            self._worker_mgr.run_task(f"job_{job_id}", _run)
        else:
            _run()

        return True

    def cancel_job(self, job_id: str) -> bool:
        job = self._active.get(job_id)
        if not job:
            db_job = self._repo.get_job(job_id)
            if db_job and db_job.status in (JobStatus.PENDING,):
                self._repo.update_status(job_id, JobStatus.CANCELLED)
                self.job_cancelled.emit(job_id)
                self.queue_count_changed.emit(self.pending_count)
                return True
            return False

        self._repo.update_status(job_id, JobStatus.CANCELLED)
        self._active.pop(job_id, None)
        self.job_cancelled.emit(job_id)
        self.queue_count_changed.emit(self.pending_count)
        return True

    def get_job(self, job_id: str) -> Job | None:
        return self._repo.get_job(job_id)

    def list_jobs(self, status: JobStatus | None = None,
                  type_filter: JobType | None = None,
                  limit: int = 100) -> list[Job]:
        return self._repo.list_jobs(status, type_filter, limit)

    # ── Queue processing ──

    def process_queue(self, max_jobs: int = 2):
        started = 0
        pending = self._repo.list_jobs(JobStatus.PENDING, limit=10)
        for job in pending:
            if len(self._active) >= self._max_concurrent:
                break
            if started >= max_jobs:
                break
            if self.start_job(job.id):
                started += 1
        return started

    def cancel_all(self):
        for job_id in list(self._active.keys()):
            self.cancel_job(job_id)
        for job in self._repo.list_jobs(JobStatus.PENDING):
            self._repo.update_status(job.id, JobStatus.CANCELLED)
            self.job_cancelled.emit(job.id)
        self.queue_count_changed.emit(self.pending_count)

    def cleanup_old_jobs(self, max_age_days: int = 7):
        import time as t
        cutoff = t.time() - max_age_days * 86400
        cutoff_str = time.strftime(
            "%Y-%m-%dT%H:%M:%S", t.gmtime(cutoff)
        )
        rows = self._repo._conn.execute(
            "SELECT id FROM job_queue WHERE finished_at < ? AND finished_at != ''",
            (cutoff_str,),
        ).fetchall()
        for (job_id,) in rows:
            self._repo.delete_job(job_id)

    # ── Internal ──

    def _complete_job(self, job_id: str, result: dict | None = None):
        self._repo.update_status(
            job_id, JobStatus.COMPLETED,
            progress=1.0, result_json=result or {},
        )
        self._active.pop(job_id, None)
        self.job_completed.emit(job_id, result or {})
        self.queue_count_changed.emit(self.pending_count)

    def _fail_job(self, job_id: str, error: str):
        self._repo.update_status(
            job_id, JobStatus.FAILED, error=error,
        )
        self._active.pop(job_id, None)
        self.job_failed.emit(job_id, error)
        self.queue_count_changed.emit(self.pending_count)
