"""Adapt Audio Lab operations to canonical WorkerManager jobs."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.audio_lab.audio_lab_contracts import (
    AudioLabErrorCode,
    AudioLabJobStatus,
    AudioLabOperation,
)
from core.worker_manager import TaskContext, TaskHandle, WorkerManager

logger = logging.getLogger("michi.audio_lab.job_adapter")


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
        self._jobs: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def submit_probe(self, filepath: str) -> str:
        return self._submit(
            AudioLabOperation.PROBE,
            "probe",
            f"Probando {filepath}",
            {"filepath": filepath},
            self._probe,
            lambda: self._probe.probe(filepath).to_dict(),
        )

    def submit_analysis(self, filepath: str) -> str:
        return self._submit(
            AudioLabOperation.ANALYSIS,
            "analysis",
            f"Analizando {filepath}",
            {"filepath": filepath},
            self._analysis,
            lambda: self._analysis.analyze_file(filepath),
        )

    def submit_replaygain(self, filepath: str) -> str:
        def run() -> dict[str, Any]:
            result = self._replaygain.analyze_track(filepath)
            self._raise_for_service_failure(result)
            return {"track_gain": result.track_gain, "status": result.status}

        return self._submit(
            AudioLabOperation.REPLAYGAIN,
            "rg",
            f"ReplayGain {filepath}",
            {"filepath": filepath},
            self._replaygain,
            run,
        )

    def submit_integrity(self, filepath: str) -> str:
        def run() -> dict[str, Any]:
            result = self._integrity.check(filepath)
            self._raise_for_service_failure(result)
            issues = [
                issue.get("type", "") if isinstance(issue, dict)
                else getattr(issue, "type", "")
                for issue in result.issues
            ]
            return {"issues": issues, "valid": result.is_valid}

        return self._submit(
            AudioLabOperation.INTEGRITY,
            "integrity",
            f"Verificando {filepath}",
            {"filepath": filepath},
            self._integrity,
            run,
        )

    def submit_comparison(self, file_a: str, file_b: str) -> str:
        def run() -> dict[str, Any]:
            result = self._comparison.compare(file_a, file_b)
            self._raise_for_service_failure(result)
            return {
                "identical": result.identical,
                "dimensions": [dimension.key for dimension in result.dimensions],
            }

        return self._submit(
            AudioLabOperation.COMPARISON,
            "compare",
            f"Comparando {file_a}",
            {"file_a": file_a, "file_b": file_b},
            self._comparison,
            run,
        )

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or not self._wm:
            return False
        handle = job.get("handle")
        if not isinstance(handle, TaskHandle):
            return False
        return self._wm.cancel_task(handle.task_id)

    def list(self, filter_status: str = "") -> list[dict[str, Any]]:
        jobs = [self._to_public(job) for job in self._jobs.values()]
        if filter_status:
            return [job for job in jobs if job["status"] == filter_status]
        return jobs

    def get(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        return self._to_public(job) if job else None

    def _submit(
        self,
        operation: AudioLabOperation,
        prefix: str,
        title: str,
        request: dict[str, Any],
        service: Any,
        operation_fn: Callable[[], Any],
    ) -> str:
        job_id = self._next_id(prefix)
        task_id = f"alab_{job_id}"
        job = {
            "id": job_id,
            "type": operation.value,
            "title": title,
            "request": dict(request),
            "progress": 0.0,
            "message": "",
            "result": None,
            "error": "",
            "error_code": "",
            "created_at": time.time(),
            "handle": None,
        }
        self._jobs[job_id] = job
        self.jobCreated.emit(job_id, operation.value)

        if not self._wm or service is None:
            self._reject_unavailable(job_id, task_id)
            return job_id

        def run(ctx: TaskContext) -> Any:
            ctx.token.raise_if_cancelled()
            ctx.report_progress(0.0, "Iniciando")
            result = operation_fn()
            self._raise_for_service_failure(result)
            ctx.token.raise_if_cancelled()
            return result

        handle = self._wm.run_task(
            task_id,
            run,
            owner="audio_lab",
            cancellable=True,
            pass_context=True,
            on_done=lambda result: self._complete(job_id, result),
            on_error=lambda code, message: self._fail(job_id, code, message),
            on_cancelled=lambda: self._cancelled(job_id),
            on_progress=lambda progress, message: self._progress(
                job_id, progress, message
            ),
        )
        job["handle"] = handle
        if handle.state == TaskHandle.TASK_FAILED and not job["error_code"]:
            self._fail(
                job_id,
                handle.error_code or AudioLabErrorCode.OPERATION_FAILED.value,
                handle.message or "No se pudo iniciar el trabajo",
            )
        return job_id

    @staticmethod
    def _raise_for_service_failure(result: Any) -> None:
        status = result.get("status", "") if isinstance(result, dict) else getattr(
            result, "status", ""
        )
        error = result.get("error", "") if isinstance(result, dict) else getattr(
            result, "error", ""
        )
        if str(status).lower() in {"error", "failed"} or error:
            raise RuntimeError(str(error) or f"Audio Lab operation returned {status}")

    def _reject_unavailable(self, job_id: str, task_id: str) -> None:
        handle = TaskHandle(task_id, owner="audio_lab", cancellable=False)
        handle.state = TaskHandle.TASK_FAILED
        handle.error_code = AudioLabErrorCode.INFRASTRUCTURE_UNAVAILABLE.value
        handle.message = "WorkerManager o servicio de Audio Lab no disponible"
        handle.finished_at = time.time()
        self._jobs[job_id]["handle"] = handle
        self._fail(job_id, handle.error_code, handle.message)

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}_{int(time.time())}"

    def _progress(self, job_id: str, value: float, message: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        progress = max(job["progress"], max(0.0, min(1.0, float(value))))
        job["progress"] = progress
        if message:
            job["message"] = str(message)
        self.jobProgress.emit(job_id, progress)

    def _complete(self, job_id: str, result: Any) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job["progress"] = 1.0
        job["result"] = result
        self.jobCompleted.emit(job_id, AudioLabJobStatus.COMPLETED.value, result)

    def _fail(self, job_id: str, code: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job["error_code"] = str(code)
        job["error"] = str(error)
        self.jobFailed.emit(job_id, str(error))

    def _cancelled(self, job_id: str) -> None:
        if job_id in self._jobs:
            self.jobCancelled.emit(job_id)

    @staticmethod
    def _to_public(job: dict[str, Any]) -> dict[str, Any]:
        handle = job.get("handle")
        status = handle.state if isinstance(handle, TaskHandle) else AudioLabJobStatus.QUEUED.value
        return {
            "id": job["id"],
            "type": job["type"],
            "title": job["title"],
            "status": status,
            "progress": job["progress"],
            "message": job["message"],
            "request": dict(job["request"]),
            "created_at": job["created_at"],
            "started_at": handle.started_at if isinstance(handle, TaskHandle) else 0.0,
            "finished_at": handle.finished_at if isinstance(handle, TaskHandle) else 0.0,
            "task_id": handle.task_id if isinstance(handle, TaskHandle) else "",
            "result": job["result"],
            "error": job["error"],
            "error_code": job["error_code"],
        }
