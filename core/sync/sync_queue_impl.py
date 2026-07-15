"""Sync queue — manages transfer jobs with progress, cancel, pause, resume."""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field


@dataclass
class SyncJob:
    job_id: str = ""
    manifest_id: str = ""
    device_id: str = ""
    status: str = "pending"
    progress: float = 0.0
    current_track: int = 0
    total_tracks: int = 0
    bytes_transferred: int = 0
    total_bytes: int = 0
    errors: list[str] = field(default_factory=list)
    created_at: str = ""
    finished_at: str = ""


class SyncQueue:
    def __init__(self):
        self._jobs: dict[str, SyncJob] = {}
        self._active_job_id: str = ""

    def create_job(self, manifest_id: str, device_id: str,
                   total_tracks: int, total_bytes: int) -> SyncJob:
        job = SyncJob(
            job_id=str(uuid.uuid4())[:12],
            manifest_id=manifest_id,
            device_id=device_id,
            status="pending",
            total_tracks=total_tracks,
            total_bytes=total_bytes,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self._jobs[job.job_id] = job
        return job

    def start_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "running"
            self._active_job_id = job_id

    def update_progress(self, job_id: str, track: int, total: int,
                        bytes_done: int, total_bytes: int):
        job = self._jobs.get(job_id)
        if job:
            job.current_track = track
            job.total_tracks = total
            job.bytes_transferred = bytes_done
            job.total_bytes = total_bytes
            job.progress = bytes_done / max(1, total_bytes)

    def complete_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "completed"
            job.progress = 1.0
            job.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._active_job_id = ""

    def cancel_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "cancelled"
            if self._active_job_id == job_id:
                self._active_job_id = ""

    def pause_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "paused"

    def resume_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "running"

    def add_error(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if job:
            job.errors.append(error)

    def get_job(self, job_id: str) -> SyncJob | None:
        return self._jobs.get(job_id)

    def get_active_job(self) -> SyncJob | None:
        return self._jobs.get(self._active_job_id)

    def get_history(self, limit: int = 20) -> list[SyncJob]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]
