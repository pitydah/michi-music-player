"""JobBridge — QML-facing background job manager.

Runs tasks synchronously by default. WorkerManager integration deferred
(QRunnable signal ownership issue in Wave IX).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.jobs")

STATE_QUEUED = "queued"
STATE_RUNNING = "running"
STATE_COMPLETED = "completed"
STATE_COMPLETED_WITH_ERRORS = "completed_with_errors"
STATE_CANCELLED = "cancelled"
STATE_FAILED = "failed"


class JobBridge(QObject):
    jobsChanged = Signal()

    def __init__(self, worker_manager=None, db=None, library_bridge=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._db = db
        self._lib = library_bridge
        self._jobs: list[dict[str, Any]] = []
        self._counter = 0

    @Property("QVariantList", notify=jobsChanged)
    def jobs(self):
        return list(self._jobs)

    @Property(int, notify=jobsChanged)
    def activeCount(self):
        return sum(1 for j in self._jobs if j["state"] in (STATE_QUEUED, STATE_RUNNING))

    def _add_job(self, job_type: str, title: str, callable_fn: Callable | None = None) -> int:
        self._counter += 1
        job_id = self._counter
        now = time.time()
        job = {
            "job_id": job_id, "type": job_type, "title": title,
            "state": STATE_QUEUED, "progress": 0.0, "processed": 0, "total": 0,
            "message": "", "error_code": "", "can_cancel": True,
            "can_retry": False, "started_at": now, "finished_at": 0,
            "duration": 0, "summary": "",
        }
        self._jobs.insert(0, job)
        self.jobsChanged.emit()

        if callable_fn:
            job["state"] = STATE_RUNNING
            self.jobsChanged.emit()
            try:
                callable_fn()
                job["state"] = STATE_COMPLETED
            except Exception as e:
                logger.debug("Job %s failed: %s", job_type, e)
                job["state"] = STATE_FAILED
                job["error_code"] = "EXECUTION_FAILED"
                job["message"] = str(e)
            job["finished_at"] = time.time()
            job["duration"] = job["finished_at"] - job["started_at"]
            self.jobsChanged.emit()

        return job_id

    def _scan_library(self, folder_path: str):
        if not self._db or not folder_path:
            return
        from pathlib import Path
        p = Path(folder_path)
        if not p.is_dir():
            return
        from library.indexer import Indexer
        worker = Indexer(self._db, str(p))
        worker.run()
        if hasattr(self._db, 'conn') and self._db.conn:
            self._db.conn.commit()
        if self._lib and hasattr(self._lib, 'refresh'):
            self._lib.refresh()

    @Slot(str, result=dict)
    def runJob(self, job_type: str, params: str = ""):
        if job_type == "library_scan":
            self._add_job(job_type, "Escaneando biblioteca",
                          lambda: self._scan_library(params))
            return {"ok": True}
        if job_type == "metadata_scan":
            return {"ok": False, "error": "UNSUPPORTED"}
        if job_type == "doctor_scan":
            return {"ok": False, "error": "UNSUPPORTED"}
        return {"ok": False, "error": "UNKNOWN_JOB_TYPE"}

    @Slot(int, result=dict)
    def cancelJob(self, job_id: int):
        for j in self._jobs:
            if j["job_id"] == job_id and j["state"] in (STATE_QUEUED, STATE_RUNNING):
                j["state"] = STATE_CANCELLED
                j["finished_at"] = time.time()
                j["duration"] = j["finished_at"] - j["started_at"]
                self.jobsChanged.emit()
                return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    @Slot(result=dict)
    def clearCompleted(self):
        self._jobs = [j for j in self._jobs if j["state"] in (STATE_QUEUED, STATE_RUNNING)]
        self.jobsChanged.emit()
        return {"ok": True}
