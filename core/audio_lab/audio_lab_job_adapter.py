"""AudioLabJobAdapter — adapts Audio Lab services to WorkerManager jobs.

Provides unified job management for all audio lab operations.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.job_adapter")

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"


class AudioLabJobAdapter(QObject):
    jobCreated = Signal(str, str)
    jobProgress = Signal(str, float)
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)
    jobCancelled = Signal(str)

    def __init__(self, db=None, wm: WorkerManager | None = None,
                 probe=None, analysis=None, conversion=None,
                 normalization=None, replaygain=None,
                 integrity=None, comparison=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._probe = probe
        self._analysis = analysis
        self._conversion = conversion
        self._normalization = normalization
        self._replaygain = replaygain
        self._integrity = integrity
        self._comparison = comparison
        self._jobs: dict[str, dict] = {}
        self._counter = 0

    def submit_probe(self, filepath: str) -> str:
        job_id = self._next_id("probe")
        self._create_job(job_id, "probe", f"Probando {filepath}")
        if self._wm and self._probe:
            self._wm.run_task(
                f"alab_{job_id}",
                lambda: self._probe.probe(filepath).to_dict(),
                owner="audio_lab",
                on_done=lambda r: self._complete(job_id, r),
                on_error=lambda c, m: self._fail(job_id, m),
                cancellable=True,
            )
        return job_id

    def submit_analysis(self, filepath: str) -> str:
        job_id = self._next_id("analysis")
        self._create_job(job_id, "analysis", f"Analizando {filepath}")
        if self._wm and self._analysis:
            self._wm.run_task(
                f"alab_{job_id}",
                lambda: self._analysis.analyze_file(filepath),
                owner="audio_lab",
                on_done=lambda r: self._complete(job_id, r),
                on_error=lambda c, m: self._fail(job_id, m),
                cancellable=True,
            )
        return job_id

    def submit_replaygain(self, filepath: str) -> str:
        job_id = self._next_id("rg")
        self._create_job(job_id, "replaygain", f"ReplayGain {filepath}")
        if self._wm and self._replaygain:
            self._wm.run_task(
                f"alab_{job_id}",
                lambda: {
                    "track_gain": self._replaygain.analyze_track(filepath).track_gain,
                    "status": self._replaygain.analyze_track(filepath).status,
                },
                owner="audio_lab",
                on_done=lambda r: self._complete(job_id, r),
                on_error=lambda c, m: self._fail(job_id, m),
                cancellable=True,
            )
        return job_id

    def submit_integrity(self, filepath: str) -> str:
        job_id = self._next_id("integrity")
        self._create_job(job_id, "integrity", f"Verificando {filepath}")
        if self._wm and self._integrity:
            self._wm.run_task(
                f"alab_{job_id}",
                lambda: {
                    "issues": [i["type"] for i in self._integrity.check(filepath).issues],
                    "valid": self._integrity.check(filepath).is_valid,
                },
                owner="audio_lab",
                on_done=lambda r: self._complete(job_id, r),
                on_error=lambda c, m: self._fail(job_id, m),
                cancellable=True,
            )
        return job_id

    def submit_comparison(self, file_a: str, file_b: str) -> str:
        job_id = self._next_id("compare")
        self._create_job(job_id, "comparison", f"Comparando {file_a}")
        if self._wm and self._comparison:
            self._wm.run_task(
                f"alab_{job_id}",
                lambda: {
                    "identical": self._comparison.compare(file_a, file_b).identical,
                    "dimensions": [d.key for d in self._comparison.compare(file_a, file_b).dimensions],
                },
                owner="audio_lab",
                on_done=lambda r: self._complete(job_id, r),
                on_error=lambda c, m: self._fail(job_id, m),
                cancellable=True,
            )
        return job_id

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job["status"] not in (JOB_STATUS_QUEUED, JOB_STATUS_RUNNING):
            return False
        handle = job.get("_handle")
        if handle and hasattr(handle, "cancel"):
            handle.cancel()
        job["status"] = JOB_STATUS_CANCELLED
        return True

    def list(self, filter_status: str = "") -> list[dict]:
        if filter_status:
            return [j for j in self._jobs.values() if j["status"] == filter_status]
        return list(self._jobs.values())

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}_{int(time.time())}"

    def _create_job(self, job_id: str, jtype: str, title: str):
        self._jobs[job_id] = {
            "id": job_id, "type": jtype, "title": title,
            "status": JOB_STATUS_QUEUED, "progress": 0.0,
            "created_at": time.time(), "result": None, "error": "",
        }
        self.jobCreated.emit(job_id, jtype)

    def _complete(self, job_id: str, result: Any):
        job = self._jobs.get(job_id)
        if job:
            job["status"] = JOB_STATUS_COMPLETED
            job["result"] = result
        self.jobCompleted.emit(job_id, "completed", result)

    def _fail(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if job:
            job["status"] = JOB_STATUS_FAILED
            job["error"] = error
        self.jobFailed.emit(job_id, error)
