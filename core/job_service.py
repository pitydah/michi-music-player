"""JobService — lightweight job tracker for device sync and other background ops."""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from contextlib import suppress
from typing import Any, Callable


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    job_id: str
    kind: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    meta: dict = field(default_factory=dict)


class JobService:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"job_{int(time.time())}_{self._counter}"

    def create(self, kind: str, meta: dict | None = None) -> Job:
        job = Job(job_id=self._next_id(), kind=kind, meta=meta or {})
        with self._lock:
            self._jobs[job.job_id] = job
        self._notify("created", job)
        return job

    def update(self, job_id: str, status: JobStatus | None = None,
               progress: float | None = None, error: str = "") -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if status is not None:
                job.status = status
                if status in (JobStatus.RUNNING,):
                    job.started_at = time.time()
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    job.finished_at = time.time()
            if progress is not None:
                job.progress = progress
            if error:
                job.error = error
        self._notify("updated", job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_by_kind(self, kind: str) -> list[Job]:
        with self._lock:
            return [j for j in self._jobs.values() if j.kind == kind]

    def list_active(self) -> list[Job]:
        with self._lock:
            return [j for j in self._jobs.values()
                    if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
                return False
            job.status = JobStatus.CANCELLED
            job.finished_at = time.time()
        self._notify("updated", job)
        return True

    def clear_completed(self):
        with self._lock:
            self._jobs = {k: v for k, v in self._jobs.items()
                          if v.status in (JobStatus.QUEUED, JobStatus.RUNNING)}

    def on(self, event: str, cb: Callable):
        with self._lock:
            self._callbacks.setdefault(event, []).append(cb)

    def off(self, event: str, cb: Callable):
        with self._lock, suppress(LookupError):
            self._callbacks[event].remove(cb)

    def _notify(self, event: str, data: Any = None):
        with self._lock:
            cbs = list(self._callbacks.get(event, []))
        for cb in cbs:
            try:
                cb(data)
            except Exception:
                continue
