"""WorkerManager — QThreadPool with CancellationToken, TaskHandle, cooperative cancel."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt

logger = logging.getLogger("michi.workers")


# ── CancellationToken (thread-safe) ──

class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self):
        if self._event.is_set():
            raise CancelledError("Task cancelled")

    def request_cancel(self):
        self._event.set()


class CancelledError(Exception):
    pass


# ── TaskHandle ──

TASK_QUEUED = "queued"
TASK_RUNNING = "running"
TASK_CANCEL_REQUESTED = "cancel_requested"
TASK_CANCELLED = "cancelled"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"


class TaskHandle:
    def __init__(self, task_id: str, token: CancellationToken | None = None,
                 owner: str = ""):
        self.task_id = task_id
        self.owner = owner
        self.state = TASK_QUEUED
        self.token = token or CancellationToken()
        self.created_at = time.time()
        self.started_at = 0.0
        self.finished_at = 0.0
        self.result: Any = None
        self.error_code = ""
        self.message = ""

    def cancel(self):
        self.token.request_cancel()
        if self.state in (TASK_QUEUED, TASK_RUNNING):
            self.state = TASK_CANCEL_REQUESTED

    @property
    def duration(self) -> float:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return 0.0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "owner": self.owner, "state": self.state,
            "created_at": self.created_at, "started_at": self.started_at,
            "finished_at": self.finished_at, "duration": self.duration,
            "error_code": self.error_code, "message": self.message,
            "has_result": self.result is not None,
        }


# ── QRunnable workers (no QObject children) ──

class _TaskWorker(QRunnable):
    def __init__(self, fn, token: CancellationToken, args=(), kwargs=None,
                 done_callback=None, error_callback=None):
        super().__init__()
        self._fn = fn
        self._token = token
        self._args = args
        self._kwargs = kwargs or {}
        self._done_cb = done_callback
        self._error_cb = error_callback
        self.setAutoDelete(True)

    def run(self):
        try:
            self._token.raise_if_cancelled()
            result = self._fn(self._token, *self._args, **self._kwargs)
            if not self._token.is_cancelled() and self._done_cb:
                self._done_cb(result)
        except CancelledError:
            pass  # cancelled, no callback
        except Exception as e:
            if self._error_cb:
                self._error_cb(str(e))


# ── Cover/Identify workers (unchanged but with QueuedConnection) ──

class _CoverLoaderWorker(QRunnable):
    def __init__(self, items, cover_size, existing_groups=None):
        super().__init__()
        self._signals = _WorkerSignals()
        self._items = items
        self._cover_size = cover_size
        self._existing = existing_groups

    def run(self):
        try:
            if self._items:
                from library.album_art import load_covers_for_albums
                result = load_covers_for_albums(self._items, self._cover_size)
                self._signals.done.emit(result)
            else:
                self._signals.done.emit([])
        except Exception as e:
            self._signals.error.emit(str(e))


class _IdentifyWorker(QRunnable):
    def __init__(self, capture_service, recognizer):
        super().__init__()
        self._signals = _WorkerSignals()
        self._capture = capture_service
        self._recognizer = recognizer

    def run(self):
        try:
            audio_bytes = self._capture.capture_once()
            if audio_bytes and self._recognizer:
                result = self._recognizer.identify(audio_bytes)
                self._signals.done.emit(result)
            else:
                self._signals.done.emit(None)
        except Exception as e:
            self._signals.error.emit(str(e))


class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)


# ── WorkerManager ──

class WorkerManager(QObject):
    covers_ready = Signal(list)
    identify_done = Signal(object)
    identify_error = Signal(str)
    task_done = Signal(str, object)
    task_error = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(4)
        self._log = logging.getLogger("michi.workers")
        self._handles: dict[str, TaskHandle] = {}
        self._lock = threading.Lock()
        self._max_history = 100

    # ── Public API ──

    def run_task(self, task_id: str, fn, *args, on_done=None, on_error=None,
                 on_progress=None, cancellable=False, owner="", **kwargs) -> TaskHandle:

        token = CancellationToken()
        handle = TaskHandle(task_id, token=token, owner=owner)

        with self._lock:
            self._handles[task_id] = handle
            self._prune_locked()

        def _run_fn(token: CancellationToken):
            result = fn(*args, **kwargs)
            return result

        def _on_task_done(tid, result):
            if tid == task_id:
                with self._lock:
                    h = self._handles.get(task_id)
                    if h:
                        h.state = TASK_COMPLETED
                        h.finished_at = time.time()
                        h.result = result
                self._prune()
                if on_done:
                    on_done(result)

        def _on_task_error(tid, error):
            if tid == task_id:
                with self._lock:
                    h = self._handles.get(task_id)
                    if h:
                        h.state = TASK_FAILED
                        h.finished_at = time.time()
                        h.error_code = "EXECUTION_FAILED"
                        h.message = error
                self._prune()
                if on_error:
                    on_error(error)

        self.task_done.connect(_on_task_done, type=Qt.ConnectionType.QueuedConnection)
        if on_error:
            self.task_error.connect(_on_task_error, type=Qt.ConnectionType.QueuedConnection)

        def _done_wrapper(result):
            self.task_done.emit(task_id, result)

        def _error_wrapper(error):
            self.task_error.emit(task_id, error)

        worker = _TaskWorker(_run_fn, token=token, done_callback=_done_wrapper,
                             error_callback=_error_wrapper)
        handle.state = TASK_RUNNING
        handle.started_at = time.time()
        self._pool.start(worker)

        return handle

    def get_task(self, task_id: str) -> TaskHandle | None:
        with self._lock:
            return self._handles.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            h = self._handles.get(task_id)
            if not h or h.state in (TASK_COMPLETED, TASK_CANCELLED, TASK_FAILED):
                return False
            h.cancel()
            self._handles[task_id] = h
            return True

    def cancel_all(self, owner: str = ""):
        with self._lock:
            targets = [tid for tid, h in self._handles.items()
                       if (not owner or h.owner == owner)
                       and h.state in (TASK_QUEUED, TASK_RUNNING)]
        for tid in targets:
            self.cancel_task(tid)

    def active_tasks(self) -> list[dict]:
        with self._lock:
            return [h.to_dict() for h in self._handles.values()
                    if h.state in (TASK_QUEUED, TASK_RUNNING)]

    def load_covers(self, items, cover_size):
        worker = _CoverLoaderWorker(items, cover_size)
        worker._signals.done.connect(self._on_covers_done, type=Qt.ConnectionType.QueuedConnection)
        worker._signals.error.connect(lambda e: self._log.warning("Cover load failed: %s", e))
        self._pool.start(worker)

    @Slot(object)
    def _on_covers_done(self, result):
        if isinstance(result, list):
            self.covers_ready.emit(result)
        else:
            self._log.warning("Cover loader returned invalid result: %r", type(result))

    def identify(self, capture_service, recognizer):
        worker = _IdentifyWorker(capture_service, recognizer)
        worker._signals.done.connect(self._on_identify_done, type=Qt.ConnectionType.QueuedConnection)
        worker._signals.error.connect(self.identify_error.emit, type=Qt.ConnectionType.QueuedConnection)
        self._pool.start(worker)

    @Slot(object)
    def _on_identify_done(self, result):
        self.identify_done.emit(result)

    def pending(self) -> int:
        return self._pool.activeThreadCount()

    def shutdown(self, timeout_ms: int = 2000):
        self.cancel_all()
        self._pool.clear()
        if not self._pool.waitForDone(timeout_ms):
            self._log.warning("WorkerManager shutdown: %d tasks still active after %dms",
                              self._pool.activeThreadCount(), timeout_ms)
        with self._lock:
            self._handles.clear()

    # ── Internal ──

    def _prune(self):
        with self._lock:
            self._prune_locked()

    def _prune_locked(self):
        if len(self._handles) > self._max_history:
            completed = [(tid, h.finished_at) for tid, h in self._handles.items()
                         if h.state in (TASK_COMPLETED, TASK_CANCELLED, TASK_FAILED)]
            completed.sort(key=lambda x: x[1])
            for tid, _ in completed[:len(completed) - self._max_history // 2]:
                del self._handles[tid]
