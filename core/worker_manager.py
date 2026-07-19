"""WorkerManager — QThreadPool with private event bus, execution_id, typed errors.

Architecture:
    WorkerEventBus (private, connected once in __init__)
    → handles all task_done/task_error/taskCancelled internally
    → public signals emit from main thread only
    → callbacks stored by execution_id, removed on terminal

Contract:
    run_task(task_id, fn, *args, owner="", cancellable=False,
             pass_context=False, on_done=None, on_error=None,
             on_cancelled=None, on_progress=None, **kwargs) -> TaskHandle
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt

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
    def __init__(self, task_id: str, owner: str, token: CancellationToken):
        self.task_id = task_id
        self.owner = owner
        self.token = token
        self._progress_cb: Callable | None = None

    def report_progress(self, percent: float, message: str = ""):
        p = max(0.0, min(1.0, float(percent)))
        if self._progress_cb:
            self._progress_cb(p, message)


_execution_counter = 0
_counter_lock = threading.Lock()


def _next_eid() -> int:
    global _execution_counter
    with _counter_lock:
        _execution_counter += 1
        return _execution_counter


class TaskHandle:
    TASK_QUEUED = "queued"
    TASK_RUNNING = "running"
    TASK_CANCEL_REQUESTED = "cancel_requested"
    TASK_CANCELLED = "cancelled"
    TASK_COMPLETED = "completed"
    TASK_FAILED = "failed"

    def __init__(self, task_id: str, owner: str = "", cancellable: bool = False):
        self.task_id = task_id
        self.execution_id = _next_eid()
        self.owner = owner
        self.cancellable = cancellable
        self.state = self.TASK_QUEUED
        self.token = CancellationToken()
        self.created_at = time.time()
        self.started_at = 0.0
        self.finished_at = 0.0
        self.result: Any = None
        self.error_code = ""
        self.message = ""

    def cancel(self) -> bool:
        if not self.cancellable:
            return False
        if self.state not in (self.TASK_QUEUED, self.TASK_RUNNING):
            return False
        self.token.request_cancel()
        self.state = self.TASK_CANCEL_REQUESTED
        return True

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


# ── Private event bus (connected once) ──

class _WorkerEventBus(QObject):
    completed = Signal(str, int, object)     # task_id, execution_id, result
    failed = Signal(str, int, str, str)      # task_id, execution_id, error, code
    cancelled = Signal(str, int)             # task_id, execution_id
    progress = Signal(str, int, float, object)  # task_id, execution_id, pct, msg


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
        except Exception as exc:
            logger.exception("TaskWorker failed")
            if self._error_cb:
                self._error_cb(str(exc), ERR_FAILED)


# ── Cover/Identify workers ──

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
        self._callbacks: dict[int, dict] = {}  # execution_id -> callbacks
        self._lock = threading.Lock()
        self._max_history = 100
        self._shutdown = False

        # Private event bus — connected once
        self._bus = _WorkerEventBus()
        self._bus.completed.connect(self._on_bus_completed, Qt.ConnectionType.QueuedConnection)
        self._bus.failed.connect(self._on_bus_failed, Qt.ConnectionType.QueuedConnection)
        self._bus.cancelled.connect(self._on_bus_cancelled, Qt.ConnectionType.QueuedConnection)
        self._bus.progress.connect(self._on_bus_progress, Qt.ConnectionType.QueuedConnection)
        self.destroyed.connect(self._on_destroyed)

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
            handle = TaskHandle(task_id, owner=owner, cancellable=cancellable)
            handle.state = TaskHandle.TASK_FAILED
            handle.error_code = ERR_SHUTDOWN
            handle.finished_at = time.time()
            return handle

        token = CancellationToken()
        handle = TaskHandle(task_id, owner=owner, cancellable=cancellable)
        handle.token = token

        with self._lock:
            if task_id in self._handles:
                old = self._handles[task_id]
                if old.state in (TaskHandle.TASK_QUEUED, TaskHandle.TASK_RUNNING,
                                 TaskHandle.TASK_CANCEL_REQUESTED):
                    handle.state = TaskHandle.TASK_FAILED
                    handle.error_code = ERR_DUPLICATE
                    handle.finished_at = time.time()
                    self._emit_public(handle, handle.state, error_code=ERR_DUPLICATE)
                    if on_error:
                        on_error(ERR_DUPLICATE, "Ya existe una tarea activa con este ID")
                    return handle
                # Completed/failed/cancelled: replace
                del self._handles[task_id]
            self._handles[task_id] = handle
            self._prune_locked()

        eid = handle.execution_id
        self._callbacks[eid] = {
            "on_done": on_done,
            "on_error": on_error,
            "on_cancelled": on_cancelled,
            "on_progress": on_progress,
        }

        self._emit_public(handle, TaskHandle.TASK_QUEUED)

        ctx = TaskContext(task_id, owner, token) if pass_context else None
        if ctx and on_progress:
            ctx._progress_cb = lambda p, m: self._bus.progress.emit(task_id, eid, p, m)

        def _run_fn():
            if ctx:
                return fn(ctx, *args, **kwargs)
            return fn(*args, **kwargs)

        def _done_wrapper(result):
            self._bus.completed.emit(task_id, eid, result)

        def _error_wrapper(error, code):
            self._bus.failed.emit(task_id, eid, error, code)

        def _cancelled_wrapper():
            self._bus.cancelled.emit(task_id, eid)

        worker = _TaskWorker(_run_fn, token=token,
                             done_cb=_done_wrapper,
                             error_cb=_error_wrapper,
                             cancelled_cb=_cancelled_wrapper)
        handle.state = TaskHandle.TASK_RUNNING
        handle.started_at = time.time()
        self._emit_public(handle, TaskHandle.TASK_RUNNING)
        self._pool.start(worker)

        return handle

    def get_task(self, task_id: str) -> TaskHandle | None:
        with self._lock:
            return self._handles.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            h = self._handles.get(task_id)
            if not h:
                return False
            if not h.cancellable:
                return False
            if h.state not in (TaskHandle.TASK_QUEUED, TaskHandle.TASK_RUNNING):
                return False
            accepted = h.cancel()
        if accepted:
            self._emit_public(h, TaskHandle.TASK_CANCEL_REQUESTED)
        return accepted

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

    def shutdown(self, timeout_ms: int = 2000):
        self._shutdown = True
        self.cancel_all()
        self._pool.clear()
        if not self._pool.waitForDone(timeout_ms):
            self._log.warning("WorkerManager shutdown: %d tasks still active after %dms",
                              self._pool.activeThreadCount(), timeout_ms)
        with self._lock:
            self._handles.clear()
            self._callbacks.clear()

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

    # ── Private bus handlers (main thread via QueuedConnection) ──

    @Slot(str, int, object)
    def _on_bus_completed(self, task_id: str, eid: int, result):
        handle = self._get_handle(task_id)
        if not handle or handle.execution_id != eid:
            return
        self._transition(handle, TaskHandle.TASK_COMPLETED, result=result)
        cbs = self._pop_callbacks(eid)
        if cbs and cbs.get("on_done"):
            cbs["on_done"](result)

    @Slot(str, int, str, str)
    def _on_bus_failed(self, task_id: str, eid: int, error: str, code: str):
        handle = self._get_handle(task_id)
        if not handle or handle.execution_id != eid:
            return
        self._transition(handle, TaskHandle.TASK_FAILED, error_code=code, message=error)
        cbs = self._pop_callbacks(eid)
        if cbs and cbs.get("on_error"):
            cbs["on_error"](code, error)

    @Slot(str, int)
    def _on_bus_cancelled(self, task_id: str, eid: int):
        handle = self._get_handle(task_id)
        if not handle or handle.execution_id != eid:
            return
        self._transition(handle, TaskHandle.TASK_CANCELLED, error_code=ERR_CANCELLED)
        cbs = self._pop_callbacks(eid)
        if cbs and cbs.get("on_cancelled"):
            cbs["on_cancelled"]()

    @Slot(str, int, float, object)
    def _on_bus_progress(self, task_id: str, eid: int, pct: float, msg: object):
        handle = self._get_handle(task_id)
        if not handle or handle.execution_id != eid:
            return
        text = str(msg) if msg else ""
        self.taskProgress.emit(task_id, pct, text)
        self.taskStateChanged.emit(task_id, TaskHandle.TASK_RUNNING)
        cbs = self._callbacks.get(eid)
        if cbs and cbs.get("on_progress"):
            cbs["on_progress"](pct, text)

    # ── Internal ──

    def _get_handle(self, task_id: str) -> TaskHandle | None:
        with self._lock:
            return self._handles.get(task_id)

    def _transition(self, handle: TaskHandle, state: str, result=None, error_code="", message=""):
        with self._lock:
            if handle.state in (TaskHandle.TASK_COMPLETED, TaskHandle.TASK_CANCELLED,
                                TaskHandle.TASK_FAILED):
                return
            handle.state = state
            handle.finished_at = time.time()
            if result is not None:
                handle.result = result
            if error_code:
                handle.error_code = error_code
            if message:
                handle.message = message
        self._emit_public(handle, state, error_code=error_code)
        self._prune()

    def _emit_public(self, handle: TaskHandle, state: str, error_code: str = ""):
        tid = handle.task_id
        if state == TaskHandle.TASK_QUEUED:
            self.taskQueued.emit(tid)
        elif state == TaskHandle.TASK_RUNNING:
            self.taskStarted.emit(tid)
        elif state == TaskHandle.TASK_COMPLETED:
            self.taskCompleted.emit(tid, handle.result)
        elif state == TaskHandle.TASK_CANCELLED:
            self.taskCancelled.emit(tid)
        elif state == TaskHandle.TASK_FAILED:
            code = error_code or handle.error_code or ERR_FAILED
            self.taskFailed.emit(tid, code, handle.message or "Error de ejecución")
        self.taskStateChanged.emit(tid, state)

    def _pop_callbacks(self, eid: int) -> dict | None:
        with self._lock:
            return self._callbacks.pop(eid, None)

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

    def _on_destroyed(self):
        self._shutdown = True
        self._pool.clear()
        self._pool.waitForDone(1000)
