"""QueryExecutor — async DB query runner using WorkerManager TaskHandle.

_finalize_request ensures exactly-one terminal signal per request.
No signals emitted under lock.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.query_executor")

_request_counter = 0
_counter_lock = threading.Lock()

STATE_QUEUED = "queued"
STATE_RUNNING = "running"
STATE_COMPLETED = "completed"
STATE_CANCEL_REQUESTED = "cancel_requested"
STATE_CANCELLED = "cancelled"
STATE_FAILED = "failed"
STATE_STALE = "stale"
STATE_SHUTDOWN = "shutdown"

ERR_QUERY_FAILED = "QUERY_FAILED"
ERR_QUERY_CANCELLED = "QUERY_CANCELLED"
ERR_QUERY_STALE = "QUERY_STALE"
ERR_QUERY_SHUTDOWN = "QUERY_SHUTDOWN"
ERR_SQLITE_BUSY = "SQLITE_BUSY"
ERR_SQLITE_LOCKED = "SQLITE_LOCKED"
ERR_SQLITE_READONLY = "SQLITE_READONLY"
ERR_SQLITE_CORRUPT = "SQLITE_CORRUPT"
ERR_DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
ERR_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERR_INVALID_QUERY = "INVALID_QUERY"

_MAX_REQUESTS = 200
_MAX_GENERATIONS = 500


def _next_id() -> int:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


class RequestRecord:
    __slots__ = ("request_id", "owner", "generation", "state", "context",
                 "cancellable", "handle", "created_at", "finished_at",
                 "terminal_emitted", "on_success", "on_error", "on_cancelled")

    def __init__(self, request_id: int, owner: str, generation: int,
                 context: dict | None, cancellable: bool):
        self.request_id = request_id
        self.owner = owner
        self.generation = generation
        self.state = STATE_QUEUED
        self.context = context or {}
        self.cancellable = cancellable
        self.handle = None
        self.created_at = 0.0
        self.finished_at = 0.0
        self.terminal_emitted = False
        self.on_success: Callable | None = None
        self.on_error: Callable | None = None
        self.on_cancelled: Callable | None = None


class QueryExecutor(QObject):
    success = Signal(int, object)
    failure = Signal(int, str, str)
    requestStateChanged = Signal(int, str)
    requestFinished = Signal(int)

    def __init__(self, worker_manager=None, parent=None, owns_worker_manager=False):
        super().__init__(parent)
        self._wm = worker_manager
        self._owns_wm = owns_worker_manager
        self._requests: dict[int, RequestRecord] = {}
        self._generations: dict[str, int] = {}
        self._lock = threading.Lock()
        self._shutdown = False

    # ── Public API ──

    def submit(self, owner: str, callable_fn: Callable,
               on_success: Callable | None = None,
               on_error: Callable | None = None,
               on_cancelled: Callable | None = None,
               request_context: dict | None = None,
               supersede: bool = True,
               cancellable: bool = True) -> int:
        request_id = _next_id()

        if self._shutdown:
            rec = RequestRecord(request_id, owner, 0, request_context, cancellable)
            rec.state = STATE_SHUTDOWN
            rec.finished_at = __import__('time').time()
            with self._lock:
                self._requests[request_id] = rec
                self._prune_locked()
            self._finalize(rec, STATE_SHUTDOWN, error_code=ERR_QUERY_SHUTDOWN,
                           message="QueryExecutor en shutdown",
                           on_error=on_error)
            return request_id

        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            if supersede:
                stale = [r for r in self._requests.values()
                         if r.owner == owner
                         and r.state in (STATE_QUEUED, STATE_RUNNING)]
                for r in stale:
                    r.state = STATE_CANCEL_REQUESTED
                    if self._wm and hasattr(self._wm, 'cancel_task'):
                        self._wm.cancel_task(f"qe_{r.request_id}")
            rec = RequestRecord(request_id, owner, gen, request_context, cancellable)
            rec.on_success = on_success
            rec.on_error = on_error
            rec.on_cancelled = on_cancelled
            self._requests[request_id] = rec
            self._prune_locked()

        self.requestStateChanged.emit(request_id, STATE_QUEUED)

        def _run():
            with self._lock:
                r = self._requests.get(request_id)
                if not r or r.state in (STATE_CANCELLED, STATE_CANCEL_REQUESTED, STATE_SHUTDOWN):
                    return {"ok": False, "error": ERR_QUERY_CANCELLED}
                r.state = STATE_RUNNING
            try:
                result = callable_fn()
                return {"ok": True, "result": result}
            except Exception as e:
                logger.error("QueryExecutor: %s failed: %s", owner, e)
                code = self._map_sqlite_error(e)
                return {"ok": False, "error": code, "message": str(e)}

        def _on_done(task_result):
            with self._lock:
                r = self._requests.get(request_id)
                if not r or r.terminal_emitted:
                    return
                if r.generation != self._generations.get(owner):
                    r.state = STATE_STALE
                    self._finalize(r, STATE_STALE, error_code=ERR_QUERY_STALE,
                                   message="Resultado obsoleto")
                    return
                if not task_result or not task_result.get("ok"):
                    code = task_result.get("error", ERR_QUERY_FAILED) if task_result else ERR_QUERY_CANCELLED
                    msg = task_result.get("message", "") if task_result else ""
                    state = STATE_CANCELLED if code == ERR_QUERY_CANCELLED else STATE_FAILED
                    r.state = state
                    self._finalize(r, state, error_code=code, message=msg)
                    return
                r.state = STATE_COMPLETED
                result = task_result["result"]
            self._finalize(r, STATE_COMPLETED, result=result)

        if self._wm and hasattr(self._wm, 'run_task'):
            handle = self._wm.run_task(
                f"qe_{request_id}", _run,
                on_done=_on_done,
                on_cancelled=lambda: _on_done({"ok": False, "error": ERR_QUERY_CANCELLED}),
                cancellable=cancellable,
                owner=owner,
            )
            with self._lock:
                r = self._requests.get(request_id)
                if r:
                    r.handle = handle
        else:
            result = _run()
            _on_done(result)

        return request_id

    def cancel(self, request_id: int):
        with self._lock:
            r = self._requests.get(request_id)
            if not r or r.state not in (STATE_QUEUED, STATE_RUNNING):
                return
            r.state = STATE_CANCEL_REQUESTED
            if self._wm and hasattr(self._wm, 'cancel_task'):
                self._wm.cancel_task(f"qe_{request_id}")
        self.requestStateChanged.emit(request_id, STATE_CANCEL_REQUESTED)

    def cancel_owner(self, owner: str):
        with self._lock:
            targets = [r for r in self._requests.values()
                       if r.owner == owner
                       and r.state in (STATE_QUEUED, STATE_RUNNING)]
        for r in targets:
            r.state = STATE_CANCEL_REQUESTED
            if self._wm and hasattr(self._wm, 'cancel_task'):
                self._wm.cancel_task(f"qe_{r.request_id}")
                self.requestStateChanged.emit(r.request_id, STATE_CANCEL_REQUESTED)

    def invalidate(self, owner: str):
        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            if len(self._generations) > _MAX_GENERATIONS:
                self._generations.clear()

    def is_stale(self, request_id: int, owner: str) -> bool:
        with self._lock:
            r = self._requests.get(request_id)
            if not r:
                return True
            return r.generation != self._generations.get(owner, 0)

    def request_state(self, request_id: int) -> str:
        with self._lock:
            r = self._requests.get(request_id)
            return r.state if r else ""

    def request_context(self, request_id: int) -> dict:
        with self._lock:
            r = self._requests.get(request_id)
            return dict(r.context) if r else {}

    def active_requests(self, owner: str = "") -> list[int]:
        with self._lock:
            return [r.request_id for r in self._requests.values()
                    if (not owner or r.owner == owner)
                    and r.state in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]

    def completed_requests(self, owner: str = "") -> list[int]:
        with self._lock:
            return [r.request_id for r in self._requests.values()
                    if r.state == STATE_COMPLETED
                    and (not owner or r.owner == owner)]

    def shutdown(self, timeout_ms: int = 2000):
        self._shutdown = True
        with self._lock:
            targets = [r for r in self._requests.values()
                       if r.state in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]
        for r in targets:
            self.cancel(r.request_id)
        if self._owns_wm and self._wm and hasattr(self._wm, 'shutdown'):
            self._wm.shutdown(timeout_ms)

    def prune_completed(self):
        with self._lock:
            self._prune_locked()

    def wait_for_idle(self, timeout_ms: int = 5000):
        import time
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            with self._lock:
                active = [r for r in self._requests.values()
                          if r.state in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]
                if not active:
                    return True
            time.sleep(0.05)
        return False

    # ── Internal ──

    def _finalize(self, rec: RequestRecord, state: str, result=None,
                  error_code="", message=""):
        if rec.terminal_emitted:
            return
        rec.terminal_emitted = True
        rec.finished_at = __import__('time').time()

        cb = None
        if state == STATE_COMPLETED:
            self.success.emit(rec.request_id, result)
            cb = rec.on_success
        elif state == STATE_CANCELLED:
            self.failure.emit(rec.request_id, error_code or ERR_QUERY_CANCELLED, message or "Cancelado")
            cb = rec.on_cancelled
        elif state == STATE_STALE:
            self.failure.emit(rec.request_id, error_code or ERR_QUERY_STALE, message or "Obsoleto")
            cb = rec.on_error
        else:  # FAILED, SHUTDOWN
            self.failure.emit(rec.request_id, error_code or ERR_QUERY_FAILED, message or "Error")
            cb = rec.on_error

        self.requestStateChanged.emit(rec.request_id, state)
        self.requestFinished.emit(rec.request_id)
        self._prune()

        if cb:
            try:
                if state == STATE_COMPLETED:
                    cb(result)
                elif state == STATE_CANCELLED:
                    cb()
                else:
                    cb(error_code, message)
            except Exception:
                logger.exception("QueryExecutor callback failed")

    def _prune(self):
        with self._lock:
            self._prune_locked()

    def _prune_locked(self):
        if len(self._requests) > _MAX_REQUESTS:
            terminal = [(rid, r) for rid, r in self._requests.items()
                        if r.state in (STATE_COMPLETED, STATE_CANCELLED,
                                       STATE_FAILED, STATE_STALE, STATE_SHUTDOWN)]
            to_remove = len(terminal) - _MAX_REQUESTS // 2
            for rid, _ in terminal[:to_remove]:
                del self._requests[rid]

    def _map_sqlite_error(self, exc: Exception) -> str:
        msg = str(exc).lower()
        try:
            import sqlite3
            if not isinstance(exc, sqlite3.DatabaseError):
                return ERR_QUERY_FAILED
        except ImportError:
            pass
        if "busy" in msg:
            return ERR_SQLITE_BUSY
        if "locked" in msg:
            return ERR_SQLITE_LOCKED
        if "readonly" in msg:
            return ERR_SQLITE_READONLY
        if "corrupt" in msg:
            return ERR_SQLITE_CORRUPT
        if "no such table" in msg or "no such column" in msg:
            return ERR_INVALID_QUERY
        return ERR_QUERY_FAILED
