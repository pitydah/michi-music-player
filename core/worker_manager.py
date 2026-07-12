"""WorkerManager — QThreadPool with TaskContext, cooperative cancel, typed errors.

Contract:
    run_task(task_id, fn, *args, owner="", cancellable=False,
             pass_context=False, on_done=None, on_error=None,
             on_cancelled=None, on_progress=None, **kwargs) -> TaskHandle

    When pass_context=True, fn receives TaskContext as first arg:
        fn(context, *args, **kwargs)
            context.token          -> CancellationToken
            context.report_progress(percent, message) -> None

    States: queued -> running -> cancel_requested -> cancelled
            queued -> running -> completed
            queued -> running -> failed
    Transitions are enforced. finished_at always set.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt
import contextlib

logger = logging.getLogger("michi.workers")

ERR_CANCELLED = "TASK_CANCELLED"
ERR_FAILED = "TASK_FAILED"
ERR_TIMEOUT = "TASK_TIMEOUT"
ERR_SHUTDOWN = "TASK_SHUTDOWN"
ERR_REJECTED = "TASK_REJECTED"
ERR_DUPLICATE = "TASK_DUPLICATE_ID"
ERR_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class CancelledError(Exception):
    pass


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


class TaskContext:
    """Passed to fn when pass_context=True. Provides token and progress reporting."""
    def __init__(self, task_id: str, owner: str, token: CancellationToken):
        self.task_id = task_id
        self.owner = owner
        self.token = token
        self._progress_cb: Callable | None = None

    def report_progress(self, percent: float, message: str = ""):
        if self._progress_cb:
            self._progress_cb(percent, message)


_execution_counter = 0

def _next_execution_id() -> int:
    global _execution_counter
    _execution_counter += 1
    return _execution_counter


class TaskHandle:
    TASK_QUEUED = "queued"
    TASK_RUNNING = "running"
    TASK_CANCEL_REQUESTED = "cancel_requested"
    TASK_CANCELLED = "cancelled"
    TASK_COMPLETED = "completed"
    TASK_FAILED = "failed"

    def __init__(self, task_id: str, owner: str = ""):
        self.task_id = task_id
        self.execution_id = _next_execution_id()
        self.owner = owner
        self.state = self.TASK_QUEUED
        self.token = CancellationToken()
        self.created_at = time.time()
        self.started_at = 0.0
        self.finished_at = 0.0
        self.result: Any = None
        self.error_code = ""
        self.message = ""

    def cancel(self):
        self.token.request_cancel()
        if self.state in (self.TASK_QUEUED, self.TASK_RUNNING):
            self.state = self.TASK_CANCEL_REQUESTED

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


# ── QRunnable (no QObject children) ──

class _TaskWorker(QRunnable):
    def __init__(self, fn, token: CancellationToken,
                 done_cb: Callable | None = None,
                 error_cb: Callable | None = None,
                 cancelled_cb: Callable | None = None,
                 args=(), kwargs=None):
        super().__init__()
        self._fn = fn
        self._token = token
        self._done_cb = done_cb
        self._error_cb = error_cb
        self._cancelled_cb = cancelled_cb
        self._args = args
        self._kwargs = kwargs or {}
        self.setAutoDelete(True)

    def run(self):
        try:
            self._token.raise_if_cancelled()
            result = self._fn(*self._args, **self._kwargs)
            if self._token.is_cancelled():
                if self._cancelled_cb:
                    self._cancelled_cb()
            elif self._done_cb:
                self._done_cb(result)
        except CancelledError:
            if self._cancelled_cb:
                self._cancelled_cb()
        except Exception as e:
            logger.exception("TaskWorker failed")
            if self._error_cb:
                self._error_cb(str(e), ERR_FAILED)


# ── Cover/Identify (unchanged) ──

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
    taskQueued = Signal(str)
    taskStarted = Signal(str)
    taskProgress = Signal(str, float, object)
    taskCompleted = Signal(str, object)
    taskCancelled = Signal(str)
    taskFailed = Signal(str, str, str)
    taskStateChanged = Signal(str, str)

    covers_ready = Signal(list)
    identify_done = Signal(object)
    identify_error = Signal(str)
    task_done = Signal(str, object)
    task_error = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(4)
        self._log = logging.getLogger("michi.workers")
        self._handles: dict[str, TaskHandle] = {}
        self._lock = threading.Lock()
        self._max_history = 100
        self._shutdown = False

    # ── Public API ──

    def run_task(self, task_id: str, fn, *args,
                 owner: str = "",
                 cancellable: bool = False,
                 pass_context: bool = False,
                 on_done: Callable | None = None,
                 on_error: Callable | None = None,
                 on_cancelled: Callable | None = None,
                 on_progress: Callable | None = None,
                 **kwargs) -> TaskHandle:
        if self._shutdown:
            handle = TaskHandle(task_id, owner=owner)
            handle.state = TaskHandle.TASK_FAILED
            handle.error_code = ERR_SHUTDOWN
            handle.finished_at = time.time()
            return handle

        token = CancellationToken()
        handle = TaskHandle(task_id, owner=owner)
        handle.token = token

        with self._lock:
            if task_id in self._handles:
                old = self._handles[task_id]
                if old.state in (TaskHandle.TASK_QUEUED, TaskHandle.TASK_RUNNING,
                                 TaskHandle.TASK_CANCEL_REQUESTED):
                    handle.state = TaskHandle.TASK_FAILED
                    handle.error_code = ERR_DUPLICATE
                    handle.finished_at = time.time()
                    return handle
            self._handles[task_id] = handle
            self._prune_locked()

        self.taskCancelled.connect(self._on_cancelled_signal, type=Qt.ConnectionType.QueuedConnection)
        self.taskQueued.emit(task_id)
        self.taskStateChanged.emit(task_id, TaskHandle.TASK_QUEUED)

        ctx = TaskContext(task_id, owner, token) if pass_context else None
        if ctx and on_progress:
            ctx._progress_cb = lambda p, m: self._on_progress(task_id, p, m, on_progress)

        def _run_fn():
            if ctx:
                return fn(ctx, *args, **kwargs)
            return fn(*args, **kwargs)

        def _on_task_done(tid, result):
            if tid != task_id:
                return
            with self._lock:
                h = self._handles.get(task_id)
                if not h or h.state == TaskHandle.TASK_CANCELLED:
                    return
                if h.execution_id != handle.execution_id:
                    return
                h.state = TaskHandle.TASK_COMPLETED
                h.finished_at = time.time()
                h.result = result
            with contextlib.suppress(TypeError):
                self.task_done.disconnect(_on_task_done)
            with contextlib.suppress(TypeError):
                self.task_error.disconnect(_on_task_error)
            self.taskCompleted.emit(task_id, result)
            self.taskStateChanged.emit(task_id, TaskHandle.TASK_COMPLETED)
            self._prune()
            if on_done:
                on_done(result)

        def _on_task_error(tid, error, code):
            if tid != task_id:
                return
            with self._lock:
                h = self._handles.get(task_id)
                if not h or h.state == TaskHandle.TASK_CANCELLED:
                    return
                if h.execution_id != handle.execution_id:
                    return
                h.state = TaskHandle.TASK_FAILED
                h.finished_at = time.time()
                h.error_code = code
                h.message = error
            with contextlib.suppress(TypeError):
                self.task_done.disconnect(_on_task_done)
            with contextlib.suppress(TypeError):
                self.task_error.disconnect(_on_task_error)
            self.taskFailed.emit(task_id, code, error)
            self.taskStateChanged.emit(task_id, TaskHandle.TASK_FAILED)
            self._prune()
            if on_error:
                on_error(code, error)

        self.task_done.connect(_on_task_done, type=Qt.ConnectionType.QueuedConnection)
        self.task_error.connect(_on_task_error, type=Qt.ConnectionType.QueuedConnection)

        def _done_wrapper(result):
            self.task_done.emit(task_id, result)

        def _error_wrapper(error, code=ERR_FAILED):
            self.task_error.emit(task_id, error, code)

        worker = _TaskWorker(
            _run_fn, token=token,
            done_cb=_done_wrapper,
            error_cb=_error_wrapper,
            cancelled_cb=lambda: self.taskCancelled.emit(task_id),
        )
        handle.state = TaskHandle.TASK_RUNNING
        handle.started_at = time.time()
        if on_cancelled:
            handle._on_cancelled_cb = [on_cancelled]
        self.taskStarted.emit(task_id)
        self.taskStateChanged.emit(task_id, TaskHandle.TASK_RUNNING)
        self._pool.start(worker)

        return handle

    def get_task(self, task_id: str) -> TaskHandle | None:
        with self._lock:
            return self._handles.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            h = self._handles.get(task_id)
            if not h or h.state in (TaskHandle.TASK_COMPLETED, TaskHandle.TASK_CANCELLED,
                                    TaskHandle.TASK_FAILED):
                return False
            h.cancel()
            return True

    def cancel_all(self, owner: str = ""):
        with self._lock:
            targets = [tid for tid, h in self._handles.items()
                       if (not owner or h.owner == owner)
                       and h.state in (TaskHandle.TASK_QUEUED, TaskHandle.TASK_RUNNING)]
        for tid in targets:
            self.cancel_task(tid)

    def active_tasks(self) -> list[dict]:
        with self._lock:
            return [h.to_dict() for h in self._handles.values()
                    if h.state in (TaskHandle.TASK_QUEUED, TaskHandle.TASK_RUNNING,
                                   TaskHandle.TASK_CANCEL_REQUESTED)]

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
        self._shutdown = True
        self.cancel_all()
        self._pool.clear()
        if not self._pool.waitForDone(timeout_ms):
            self._log.warning("WorkerManager shutdown: %d tasks still active after %dms",
                              self._pool.activeThreadCount(), timeout_ms)
        with self._lock:
            self._handles.clear()

    @Slot(str)
    def _on_cancelled_signal(self, task_id: str):
        with self._lock:
            h = self._handles.get(task_id)
            if not h or h.state == TaskHandle.TASK_CANCELLED:
                return
            h.state = TaskHandle.TASK_CANCELLED
            h.finished_at = time.time()
            h.error_code = ERR_CANCELLED
        self.taskStateChanged.emit(task_id, TaskHandle.TASK_CANCELLED)
        self._prune()
        handle = self.get_task(task_id)
        if handle:
            callbacks = getattr(handle, '_on_cancelled_cb', None)
            if callbacks:
                for cb in callbacks:
                    try:
                        cb()
                    except Exception:
                        logger.exception("on_cancelled callback failed")

    def _on_progress(self, task_id: str, percent: float, msg: str, cb: Callable):
        self.taskProgress.emit(task_id, percent, msg)
        if cb:
            cb(percent, msg)

    def _prune(self):
        with self._lock:
            self._prune_locked()

    def _prune_locked(self):
        if len(self._handles) > self._max_history:
            completed = [(tid, h.finished_at) for tid, h in self._handles.items()
                         if h.state in (TaskHandle.TASK_COMPLETED, TaskHandle.TASK_CANCELLED,
                                        TaskHandle.TASK_FAILED)]
            completed.sort(key=lambda x: x[1] if x[1] else 0)
            for tid, _ in completed[:len(completed) - self._max_history // 2]:
                del self._handles[tid]
