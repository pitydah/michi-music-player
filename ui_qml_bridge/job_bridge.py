"""JobBridge — QML-facing async job manager via WorkerManager TaskHandle."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.jobs")

STATE_QUEUED = "queued"
STATE_RUNNING = "running"
STATE_COMPLETED = "completed"
STATE_COMPLETED_WITH_ERRORS = "completed_with_errors"
STATE_CANCELLED = "cancelled"
STATE_FAILED = "failed"
STATE_CANCEL_REQUESTED = "cancel_requested"

_MAX_JOBS = 200


class JobBridge(QObject):
    jobsChanged = Signal()

    def __init__(self, worker_manager: WorkerManager | None = None,
                 db=None, library_bridge=None, parent=None):
        super().__init__(parent)
        assert worker_manager is not None, "JobBridge: worker_manager is REQUIRED"
        assert db is not None, "JobBridge: db is REQUIRED"
        self._wm = worker_manager
        self._db = db
        self._lib = library_bridge
        self._jobs: list[dict[str, Any]] = []
        self._counter = 0
        self._library_coordinator = None

    def attach_library_coordinator(self, coordinator: object):
        self._library_coordinator = coordinator

    @Property("QVariantList", notify=jobsChanged)
    def jobs(self):
        return list(self._jobs)

    @Property(int, notify=jobsChanged)
    def activeCount(self):
        return sum(1 for j in self._jobs if j["state"] in
                   (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED))

    def _add_job(self, job_type: str, title: str,
                 callable_fn: Callable | None = None) -> int:
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

        if callable_fn and self._wm and hasattr(self._wm, 'run_task'):
            task_id = f"job_{job_id}"

            def _run():
                try:
                    callable_fn()
                    return {"ok": True}
                except Exception as e:
                    return {"ok": False, "error": str(e)}

            def _done(result):
                self._update_job(job_id, state=STATE_COMPLETED if result.get("ok")
                                 else STATE_FAILED,
                                 finished_at=time.time(),
                                 error_code="" if result.get("ok") else "EXECUTION_FAILED",
                                 message=result.get("error", ""))

            handle = self._wm.run_task(task_id, _run, on_done=_done,
                                       cancellable=True, owner="jobs")
            job["_handle"] = handle
            job["_task_id"] = task_id
            job["state"] = STATE_RUNNING
            self.jobsChanged.emit()
        elif callable_fn:
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

        self._prune()
        return job_id

    def _update_job(self, job_id: int, **kwargs):
        for j in self._jobs:
            if j["job_id"] == job_id:
                for k, v in kwargs.items():
                    if k != "_handle" and k != "_task_id":
                        j[k] = v
                if "finished_at" in kwargs and kwargs["finished_at"]:
                    j["duration"] = kwargs["finished_at"] - j["started_at"]
                self.jobsChanged.emit()
                return

    def _scan_library(self, folder_path: str):
        from core.scanner_job_adapter import ScannerJobAdapter
        adapter = ScannerJobAdapter(self._db, self._lib)
        return adapter.scan(folder_path)

    @Slot(str, result=dict)
    def runJob(self, job_type: str, params: str = ""):
        if job_type == "library_scan":
            self._add_job(job_type, "Escaneando biblioteca",
                          lambda: self._scan_library(params))
            return {"ok": True}
        if job_type == "library_scan_all":
            self._add_job(job_type, "Escaneando todas las fuentes",
                          lambda: self._scan_all_sources())
            return {"ok": True}
        if job_type == "metadata_scan":
            self._add_job(job_type, "Analizando metadatos",
                          lambda: self._run_metadata_scan())
            return {"ok": True}
        if job_type == "doctor_scan":
            self._add_job(job_type, "Revisando biblioteca",
                          lambda: self._run_doctor_scan())
            return {"ok": True}
        return {"ok": False, "error": "UNKNOWN_JOB_TYPE"}

    def _run_metadata_scan(self):
        from core.metadata_batch_adapter import MetadataBatchAdapter
        adapter = MetadataBatchAdapter(db=self._db)
        return adapter.scan_missing()

    def _run_doctor_scan(self):
        from core.metadata_batch_adapter import LibraryDoctorAdapter
        adapter = LibraryDoctorAdapter(db=self._db)
        return adapter.scan()

    def _scan_all_sources(self):
        try:
            from core.library_sources_service import LibrarySourcesService
            svc = LibrarySourcesService(db=self._db)
            for source in svc.list():
                if source.get("enabled") and source.get("available"):
                    self._scan_library(source["path"])
        except Exception:
            pass

    @Slot(int, result=dict)
    def cancelJob(self, job_id: int):
        for j in self._jobs:
            if j["job_id"] == job_id:
                handle = j.get("_handle")
                if handle and hasattr(handle, 'cancel'):
                    handle.cancel()
                j["state"] = STATE_CANCELLED
                j["finished_at"] = time.time()
                j["duration"] = j["finished_at"] - j["started_at"]
                self.jobsChanged.emit()
                return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    @Slot(int, result=dict)
    def retryJob(self, job_id: int):
        for j in self._jobs:
            if j["job_id"] == job_id and j["state"] in (STATE_FAILED, STATE_CANCELLED):
                fn = j.get("_fn")
                if fn:
                    return self.runJob(j["type"])
                return {"ok": False, "error": "NO_CALLABLE"}
        return {"ok": False, "error": "NOT_FOUND"}

    @Slot(result=dict)
    def clearCompleted(self):
        self._jobs = [j for j in self._jobs if j["state"]
                      in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]
        self.jobsChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearFailed(self):
        self._jobs = [j for j in self._jobs if j["state"]
                      not in (STATE_FAILED, STATE_COMPLETED, STATE_COMPLETED_WITH_ERRORS)]
        self.jobsChanged.emit()
        return {"ok": True}

    def _prune(self):
        if len(self._jobs) > _MAX_JOBS:
            completed = [(i, j) for i, j in enumerate(self._jobs)
                         if j["state"] in (STATE_COMPLETED, STATE_FAILED,
                                           STATE_COMPLETED_WITH_ERRORS, STATE_CANCELLED)]
            to_remove = len(completed) - _MAX_JOBS // 2
            for idx, _ in sorted(completed[:to_remove], key=lambda x: -x[0]):
                if idx < len(self._jobs):
                    self._jobs.pop(idx)
