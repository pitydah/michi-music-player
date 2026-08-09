"""JobBridge — thin QML view over DurableJobService (ADR-004).

Exposes durable jobs (persisted, async, cooperative cancellation) to QML
with the same observable vocabulary the previous in-memory bridge used
(job_id/type/title/state/progress/message/error_code/can_cancel/can_retry/
duration). No internal registry, no scheduling, no synchronous execution:
every operation delegates to the injected ``job_service``. Without one the
bridge degrades to explicit INFRASTRUCTURE_UNAVAILABLE errors.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.jobs.job_service import JobState

logger = logging.getLogger("michi.jobs")

INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE"

QML_STATE_MAP = {
    JobState.QUEUED: "queued",
    JobState.RUNNING: "running",
    JobState.PAUSING: "paused",
    JobState.PAUSED: "paused",
    JobState.CANCELLING: "cancel_requested",
    JobState.CANCELLED: "cancelled",
    JobState.SUCCEEDED: "completed",
    JobState.PARTIAL_SUCCESS: "completed_with_errors",
    JobState.FAILED: "failed",
    JobState.INTERRUPTED: "failed",
}

TITLE_BY_TYPE = {
    "analysis": "Análisis técnico",
    "library_scan": "Escaneando biblioteca",
    "library_scan_all": "Escaneando todas las fuentes",
    "metadata_scan": "Analizando metadatos",
    "doctor_scan": "Revisando biblioteca",
    "metadata_batch": "Edición de metadatos en lote",
    "history_export": "Exportando historial",
}

_TIME_FMT = "%Y-%m-%dT%H:%M:%S"


class JobBridge(QObject):
    jobsChanged = Signal()

    def __init__(self, job_service=None, worker_manager=None,
                 db=None, library_bridge=None, parent=None):
        super().__init__(parent)
        del worker_manager, db  # backward-compat kwargs, superseded by job_service
        self._js = job_service
        self._lib = library_bridge
        self._library_coordinator = None
        if self._js is None:
            logger.warning(
                "JobBridge: job_service is None — degraded mode "
                "(INFRASTRUCTURE_UNAVAILABLE)"
            )
            return
        self._js.jobCreated.connect(self._emit_jobs_changed)
        self._js.jobStarted.connect(self._emit_jobs_changed)
        self._js.jobProgress.connect(self._emit_jobs_changed)
        self._js.jobCancelled.connect(self._emit_jobs_changed)
        self._js.jobCompleted.connect(self._on_job_completed)
        self._js.jobFailed.connect(self._emit_jobs_changed)
        self._js.queueChanged.connect(self._emit_jobs_changed)

    def _emit_jobs_changed(self, *_args):
        self.jobsChanged.emit()

    def attach_library_coordinator(self, coordinator: object):
        self._library_coordinator = coordinator

    def set_library_bridge(self, library_bridge):
        self._lib = library_bridge

    def _on_job_completed(self, job_id: str, result: Any):
        self.jobsChanged.emit()
        job = self._js.get_job(job_id)
        if (job and job.type in ("library_scan", "library_scan_all")
                and self._lib is not None
                and hasattr(self._lib, "refresh")):
            try:
                self._lib.refresh()
            except Exception:
                logger.debug("JobBridge: library refresh after scan failed",
                             exc_info=True)

    @Property("QVariantList", notify=jobsChanged)
    def jobs(self):
        if self._js is None:
            return []
        return [self._job_to_qml(d) for d in self._js.list_jobs(limit=200)]

    @Property(int, notify=jobsChanged)
    def activeCount(self):
        if self._js is None:
            return 0
        active = (JobState.QUEUED, JobState.RUNNING, JobState.CANCELLING)
        return sum(1 for d in self._js.list_jobs(limit=500)
                   if d["state"] in {s.value for s in active})

    @Property(int, notify=jobsChanged)
    def failedCount(self):
        if self._js is None:
            return 0
        return sum(1 for d in self._js.list_jobs(limit=500)
                   if d["state"] == JobState.FAILED.value)

    def _job_to_qml(self, d: dict) -> dict:
        state = d.get("state", JobState.QUEUED.value)
        try:
            qml_state = QML_STATE_MAP.get(JobState(state), "queued")
        except ValueError:
            qml_state = "queued"
        errors = d.get("errors") or []
        payload = d.get("payload") or {}
        job_type = d.get("type", "")
        return {
            "job_id": d.get("id", ""),
            "id": d.get("id", ""),
            "type": job_type,
            "kind": job_type,
            "title": d.get("title")
                     or TITLE_BY_TYPE.get(job_type, job_type or "Trabajo"),
            "state": qml_state,
            "status": qml_state,
            "progress": d.get("progress", 0.0),
            "processed": d.get("current", 0),
            "total": d.get("total", 0),
            "message": d.get("message", ""),
            "error": errors[0] if errors else "",
            "error_code": errors[0] if errors else "",
            "can_cancel": bool(d.get("cancellable"))
                          and qml_state in ("queued", "running",
                                            "cancel_requested"),
            "can_retry": bool(d.get("retryable"))
                         and qml_state in ("failed", "cancelled"),
            "duration": self._duration(d),
            "path": payload.get("folder_path", "")
                    if job_type == "library_scan" else "",
        }

    @staticmethod
    def _duration(d: dict) -> float:
        started = d.get("startedAt") or ""
        finished = d.get("finishedAt") or ""
        if not started or not finished:
            return 0.0
        try:
            return max(
                0.0,
                time.mktime(time.strptime(finished, _TIME_FMT))
                - time.mktime(time.strptime(started, _TIME_FMT)),
            )
        except (ValueError, OSError):
            return 0.0

    def _create_and_start(self, job_type: str, payload: dict,
                          owner: str = "job_bridge") -> dict:
        job_id = self._js.create_job(
            job_type, owner=owner, payload=payload,
            cancellable=True, pausable=True, retryable=True,
        )
        if not self._js.start_job(job_id):
            return {"ok": False, "error": "JOB_START_FAILED", "job_id": job_id}
        return {"ok": True, "job_id": job_id}

    @Slot(str, result=dict)
    def runJob(self, job_type: str, params: str = ""):
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        if job_type == "library_scan":
            return self._create_and_start(
                job_type, {"folder_path": params})
        if job_type in ("library_scan_all", "metadata_scan", "doctor_scan"):
            return self._create_and_start(job_type, {})
        return {"ok": False, "error": "UNKNOWN_JOB_TYPE"}

    def _add_job(self, job_type: str, title: str,
                 callable_fn: Callable | None = None,
                 params: dict | None = None) -> dict:
        """Create a durable job (kept for callers of the legacy bridge API).

        The callable is deliberately ignored: durable jobs execute through
        their registered production handler, never inline.
        """
        del callable_fn, title
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        return self._create_and_start(job_type, dict(params or {}))

    def exportHistoryAsync(self, filepath: str, fmt: str = "json",
                           filters: dict | None = None) -> dict:
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        if not filepath:
            return {"ok": False, "error": "EMPTY_PATH"}
        result = self._create_and_start(
            "history_export",
            {"filepath": filepath, "fmt": fmt, "filters": dict(filters or {})},
            owner="history_bridge",
        )
        result["async"] = True
        return result

    @Slot("QVariant", result=dict)
    def cancelJob(self, job_id):
        jid = str(job_id)
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        if self._js.get_job(jid) is None:
            return {"ok": False, "error": "NOT_FOUND"}
        if self._js.cancel_job(jid):
            return {"ok": True}
        return {"ok": False, "error": "NOT_CANCELLABLE", "job_id": jid}

    @Slot("QVariant", result=dict)
    def retryJob(self, job_id):
        """Re-queue and start a terminal job through job_service.retry_job.

        Unified semantics with NotificationActionService.retry: preserves
        the original payload, starts immediately when capacity allows and
        returns the REAL read-back state (never a blind success).
        """
        jid = str(job_id)
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        if self._js.get_job(jid) is None:
            return {"ok": False, "error": "NOT_FOUND"}
        if not self._js.retry_job(jid):
            return {"ok": False, "error": "NOT_RETRYABLE", "job_id": jid}
        job = self._js.get_job(jid)
        state = job.state.value if job else JobState.QUEUED.value
        return {"ok": True, "job_id": jid, "state": state}

    @Slot(result=dict)
    def clearCompleted(self):
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        removed = 0
        terminal = {s.value for s in (JobState.SUCCEEDED, JobState.PARTIAL_SUCCESS,
                                      JobState.CANCELLED, JobState.INTERRUPTED)}
        for d in self._js.list_jobs(limit=500):
            if d["state"] in terminal and self._js.delete_job(d["id"]):
                removed += 1
        return {"ok": True, "removed": removed}

    @Slot(result=dict)
    def clearFailed(self):
        if self._js is None:
            return {"ok": False, "error": INFRASTRUCTURE_UNAVAILABLE}
        removed = 0
        for d in self._js.list_jobs(limit=500):
            if d["state"] == JobState.FAILED.value and self._js.delete_job(d["id"]):
                removed += 1
        return {"ok": True, "removed": removed}
