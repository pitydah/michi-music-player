"""JobBridge — QML-facing background job manager via WorkerManager."""
from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.jobs")


class JobBridge(QObject):
    jobsChanged = Signal()

    def __init__(self, worker_manager=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._jobs: list[dict[str, Any]] = []
        self._counter = 0

    @Property("QVariantList", notify=jobsChanged)
    def jobs(self):
        return list(self._jobs)

    @Property(int, notify=jobsChanged)
    def activeCount(self):
        return sum(1 for j in self._jobs if j["state"] in ("queued", "running"))

    def _add_job(self, job_type: str, title: str, callable_fn=None) -> int:
        self._counter += 1
        job_id = self._counter
        job = {
            "job_id": job_id, "type": job_type, "title": title,
            "state": "queued", "progress": 0, "processed": 0, "total": 0,
            "message": "", "error_code": "", "can_cancel": True,
            "can_retry": False, "started_at": time.time(), "finished_at": 0,
            "duration": 0, "summary": "",
        }
        self._jobs.insert(0, job)
        self.jobsChanged.emit()

        if self._wm and callable_fn and hasattr(self._wm, 'run'):

            def _run():
                try:
                    callable_fn()
                    return {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}

            def _done(result):
                for j in self._jobs:
                    if j["job_id"] == job_id:
                        j["state"] = "completed" if result and result.get("ok") else "failed"
                        j["finished_at"] = time.time()
                        j["duration"] = j["finished_at"] - j["started_at"]
                        if not result or not result.get("ok"):
                            j["error_code"] = "EXECUTION_FAILED"
                            j["message"] = str(result.get("error", "")) if result else "Unknown"
                        self.jobsChanged.emit()
                        return

            self._wm.run(_run, callback=_done)

        return job_id

    def _update(self, job_id: int, **kwargs):
        for j in self._jobs:
            if j["job_id"] == job_id:
                j.update(kwargs)
                self.jobsChanged.emit()
                return

    @Slot(str, result=dict)
    def runJob(self, job_type: str):
        if job_type == "library_scan":
            return {"ok": False, "error": "UNSUPPORTED"}
        if job_type == "metadata_scan":
            return {"ok": False, "error": "UNSUPPORTED"}
        if job_type == "doctor_scan":
            return {"ok": False, "error": "UNSUPPORTED"}
        return {"ok": False, "error": "UNKNOWN_JOB_TYPE"}

    @Slot(int, result=dict)
    def cancelJob(self, job_id: int):
        for j in self._jobs:
            if j["job_id"] == job_id and j["state"] in ("queued", "running"):
                j["state"] = "cancelled"
                j["finished_at"] = time.time()
                j["duration"] = j["finished_at"] - j["started_at"]
                self.jobsChanged.emit()
                return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    @Slot(result=dict)
    def clearCompleted(self):
        self._jobs = [j for j in self._jobs if j["state"] in ("queued", "running")]
        self.jobsChanged.emit()
        return {"ok": True}
