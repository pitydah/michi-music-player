"""AudioLabJobController — centralizes job lifecycle for all Audio Lab operations.

Each job tracks: id, type, status, cancel_event, process_handle, thread, callback.
cancel() terminates the process and waits for the thread before marking cancelled.
"""
from __future__ import annotations

import logging
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("michi.audio_lab.jobs")


@dataclass
class AudioLabJob:
    job_id: str
    job_type: str
    status: str = "pending"
    cancel_event: threading.Event = field(default_factory=threading.Event)
    process_handle: subprocess.Popen | None = None
    thread: threading.Thread | None = None
    callback: Callable | None = None
    result: dict[str, Any] | None = None


class AudioLabJobController:
    def __init__(self):
        self._jobs: dict[str, AudioLabJob] = {}

    def create_job(self, job_id: str, job_type: str) -> AudioLabJob:
        job = AudioLabJob(job_id=job_id, job_type=job_type)
        self._jobs[job_id] = job
        return job

    def attach_process(self, job_id: str, process: subprocess.Popen):
        job = self._jobs.get(job_id)
        if job:
            job.process_handle = process

    def attach_thread(self, job_id: str, thread: threading.Thread):
        job = self._jobs.get(job_id)
        if job:
            job.thread = thread

    def attach_callback(self, job_id: str, callback: Callable):
        job = self._jobs.get(job_id)
        if job:
            job.callback = callback

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"ok": False, "error": "JOB_NOT_FOUND"}
        if job.status in ("completed", "failed", "cancelled"):
            return {"ok": False, "error": "JOB_ALREADY_FINISHED"}

        job.cancel_event.set()

        if job.process_handle and job.process_handle.poll() is None:
            try:
                job.process_handle.terminate()
                job.process_handle.wait(timeout=5)
            except Exception as e:
                logger.warning("Failed to terminate process for job %s: %s", job_id, e)
                try:
                    job.process_handle.kill()
                except Exception:
                    pass

        if job.thread and job.thread.is_alive():
            job.thread.join(timeout=3)

        job.status = "cancelled"
        logger.info("Job %s cancelled", job_id)
        return {"ok": True, "status": "cancelled", "job_id": job_id}

    def get_job(self, job_id: str) -> AudioLabJob | None:
        return self._jobs.get(job_id)

    def cancel_by_type(self, job_type: str) -> list[str]:
        cancelled = []
        for jid, job in list(self._jobs.items()):
            if job.job_type == job_type and job.status not in ("completed", "failed", "cancelled"):
                self.cancel(jid)
                cancelled.append(jid)
        return cancelled

    def cleanup(self, job_id: str):
        self._jobs.pop(job_id, None)

    def cleanup_all(self):
        for jid in list(self._jobs.keys()):
            if self._jobs[jid].status in ("completed", "failed", "cancelled"):
                self._jobs.pop(jid)
