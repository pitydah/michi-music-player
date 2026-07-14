"""AudioBatchService — batch processing for audio lab operations.

Manages queue, active, history, progress per file, global progress,
speed, ETA, warnings, errors, retry, cancel, pause/resume.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.batch")


@dataclass
class BatchItem:
    filepath: str = ""
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    result: dict = field(default_factory=dict)


@dataclass
class BatchJob:
    id: str = ""
    type: str = ""
    status: str = "pending"
    items: list[BatchItem] = field(default_factory=list)
    progress: float = 0.0
    speed: float = 0.0
    eta: float = 0.0
    warnings: int = 0
    errors: int = 0
    created_at: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0
    cancellable: bool = True
    pausable: bool = True
    paused: bool = False


class AudioBatchService(QObject):
    batchStarted = Signal(str)
    batchProgress = Signal(str, float, int, int)
    batchCompleted = Signal(str, object)
    batchCancelled = Signal(str)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._active: dict[str, BatchJob] = {}
        self._history: list[BatchJob] = []
        self._max_history = 50

    def create_batch(self, filepaths: list[str], job_type: str = "batch") -> str:
        batch_id = f"batch_{int(time.time() * 1000)}"
        items = [BatchItem(filepath=fp) for fp in filepaths]
        job = BatchJob(
            id=batch_id, type=job_type, items=items,
            created_at=time.time(), cancellable=True, pausable=True,
        )
        self._active[batch_id] = job
        return batch_id

    def start(self, batch_id: str, processor: Callable[[str], dict] | None = None):
        job = self._active.get(batch_id)
        if not job:
            return
        job.status = "running"
        job.started_at = time.time()
        self.batchStarted.emit(batch_id)

        for item in job.items:
            if job.paused:
                break
            if job.status == "cancelled":
                break
            item.status = "running"
            item.started_at = time.time()
            try:
                if processor:
                    item.result = processor(item.filepath)
                item.status = "completed"
                item.progress = 1.0
            except Exception as e:
                item.status = "error"
                item.error = str(e)
                job.errors += 1
            item.finished_at = time.time()
            self._recalc_progress(job)
            self.batchProgress.emit(batch_id, job.progress, job.errors, len(job.items))

        job.status = "completed" if job.errors == 0 else "completed_with_errors"
        job.finished_at = time.time()
        self.batchCompleted.emit(batch_id, {"errors": job.errors, "total": len(job.items)})
        self._archive(batch_id)

    def cancel(self, batch_id: str) -> bool:
        job = self._active.get(batch_id)
        if not job or job.status not in ("pending", "running", "paused"):
            return False
        job.status = "cancelled"
        job.finished_at = time.time()
        for item in job.items:
            if item.status in ("pending", "running"):
                item.status = "cancelled"
        self.batchCancelled.emit(batch_id)
        self._archive(batch_id)
        return True

    def pause(self, batch_id: str) -> bool:
        job = self._active.get(batch_id)
        if not job or not job.pausable or job.status != "running":
            return False
        job.paused = True
        job.status = "paused"
        return True

    def resume(self, batch_id: str) -> bool:
        job = self._active.get(batch_id)
        if not job or job.status != "paused":
            return False
        job.paused = False
        job.status = "running"
        return True

    def status(self, batch_id: str) -> dict | None:
        job = self._active.get(batch_id) or next((j for j in self._history if j.id == batch_id), None)
        if not job:
            return None
        return {
            "id": job.id, "type": job.type, "status": job.status,
            "progress": job.progress, "errors": job.errors,
            "warnings": job.warnings, "total": len(job.items),
            "eta": job.eta, "speed": job.speed,
        }

    def _recalc_progress(self, job: BatchJob):
        if not job.items:
            return
        completed = sum(1 for i in job.items if i.status in ("completed", "error", "cancelled"))
        job.progress = completed / len(job.items)
        elapsed = time.time() - job.started_at
        job.speed = completed / elapsed if elapsed > 0 else 0
        remaining = len(job.items) - completed
        job.eta = remaining / job.speed if job.speed > 0 else 0

    def _archive(self, batch_id: str):
        job = self._active.pop(batch_id, None)
        if job:
            self._history.insert(0, job)
            if len(self._history) > self._max_history:
                self._history.pop()

    def active_batches(self) -> list[dict]:
        return [self.status(bid) for bid in list(self._active.keys()) if self.status(bid)]
