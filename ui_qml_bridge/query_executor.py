"""QueryExecutor — async DB query runner using WorkerManager TaskHandle.

Contract:
    submit(owner, fn, on_success=None, on_error=None) -> request_id
    cancel(request_id)
    invalidate(owner)
    is_stale(request_id, owner) -> bool
    shutdown()
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

ERR_QUERY_FAILED = "QUERY_FAILED"
ERR_QUERY_CANCELLED = "QUERY_CANCELLED"
ERR_QUERY_STALE = "QUERY_STALE"
ERR_SQLITE_BUSY = "SQLITE_BUSY"
ERR_SQLITE_LOCKED = "SQLITE_LOCKED"
ERR_SQLITE_THREAD = "SQLITE_THREAD_ERROR"
ERR_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERR_SHUTDOWN = "SHUTDOWN"

_MAX_REQUESTS = 200


def _next_id() -> int:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


class QueryExecutor(QObject):
    success = Signal(int, object)
    failure = Signal(int, str, str)
    requestStateChanged = Signal(int, str)
    requestFinished = Signal(int)

    def __init__(self, worker_manager=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._requests: dict[int, dict] = {}
        self._generations: dict[str, int] = {}
        self._lock = threading.Lock()
        self._shutdown = False

    def submit(self, owner: str, callable_fn: Callable,
               on_success: Callable | None = None,
               on_error: Callable | None = None,
               request_context: dict | None = None,
               supersede: bool = True,
               cancellable: bool = True) -> int:
        request_id = _next_id()

        with self._lock:
            if self._shutdown:
                return 0
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            if supersede:
                stale = [rid for rid, r in self._requests.items()
                         if r.get("owner") == owner and r["state"] in (STATE_QUEUED, STATE_RUNNING)]
                for rid in stale:
                    self._requests[rid]["state"] = STATE_CANCELLED
            self._requests[request_id] = {
                "request_id": request_id, "owner": owner,
                "generation": gen, "state": STATE_QUEUED,
                "context": request_context or {},
                "cancellable": cancellable,
            }
            self._prune_locked()

        self.requestStateChanged.emit(request_id, STATE_QUEUED)

        def _run():
            with self._lock:
                req = self._requests.get(request_id)
                if not req or req["state"] == STATE_CANCELLED:
                    return {"ok": False, "error": ERR_QUERY_CANCELLED}
                req["state"] = STATE_RUNNING
            self.requestStateChanged.emit(request_id, STATE_RUNNING)
            try:
                result = callable_fn()
                return {"ok": True, "result": result}
            except Exception as e:
                logger.error("QueryExecutor: %s failed: %s", owner, e)
                return {"ok": False, "error": str(e)}

        def _on_done(task_result):
            if self._shutdown:
                return
            with self._lock:
                req = self._requests.get(request_id)
                if not req:
                    return
                if req["generation"] != self._generations.get(owner):
                    req["state"] = STATE_STALE
                    self._emit_failure(request_id, ERR_QUERY_STALE, "Resultado obsoleto", on_error)
                    self._finish(request_id)
                    return
                if not task_result or not task_result.get("ok"):
                    code = task_result.get("error", ERR_QUERY_FAILED) if task_result else ERR_QUERY_CANCELLED
                    req["state"] = STATE_FAILED if code != ERR_QUERY_CANCELLED else STATE_CANCELLED
                    self._emit_failure(request_id, code, "Error de consulta", on_error)
                    self._finish(request_id)
                    return
                req["state"] = STATE_COMPLETED
            result = task_result["result"]
            self.success.emit(request_id, result)
            self.requestStateChanged.emit(request_id, STATE_COMPLETED)
            self.requestFinished.emit(request_id)
            if on_success:
                try:
                    on_success(result)
                except Exception:
                    logger.exception("QueryExecutor on_success failed")
            self._prune()

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(
                f"qe_{request_id}", _run,
                on_done=_on_done,
                cancellable=cancellable,
                owner=owner,
            )
        else:
            result = _run()
            _on_done(result)

        return request_id

    def cancel(self, request_id: int):
        with self._lock:
            req = self._requests.get(request_id)
            if req and req["state"] in (STATE_QUEUED, STATE_RUNNING):
                req["state"] = STATE_CANCEL_REQUESTED
                self.requestStateChanged.emit(request_id, STATE_CANCEL_REQUESTED)
                if self._wm and hasattr(self._wm, 'cancel_task'):
                    self._wm.cancel_task(f"qe_{request_id}")

    def cancel_owner(self, owner: str):
        with self._lock:
            targets = [rid for rid, r in self._requests.items()
                       if r.get("owner") == owner
                       and r["state"] in (STATE_QUEUED, STATE_RUNNING)]
        for rid in targets:
            self.cancel(rid)

    def invalidate(self, owner: str):
        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen

    def is_stale(self, request_id: int, owner: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return True
            return req.get("generation", 0) != self._generations.get(owner, 0)

    def request_state(self, request_id: int) -> str:
        with self._lock:
            req = self._requests.get(request_id)
            return req["state"] if req else ""

    def active_requests(self, owner: str = "") -> list[int]:
        with self._lock:
            return [rid for rid, r in self._requests.items()
                    if (not owner or r.get("owner") == owner)
                    and r["state"] in (STATE_QUEUED, STATE_RUNNING)]

    def shutdown(self):
        self._shutdown = True
        with self._lock:
            targets = [rid for rid, r in self._requests.items()
                       if r["state"] in (STATE_QUEUED, STATE_RUNNING)]
        for rid in targets:
            self.cancel(rid)

    def prune_completed(self):
        with self._lock:
            self._prune_locked()

    def _finish(self, request_id: int):
        self.requestFinished.emit(request_id)
        self._prune()

    def _emit_failure(self, request_id: int, code: str, msg: str, on_error: Callable | None):
        self.failure.emit(request_id, code, msg)
        self.requestStateChanged.emit(request_id, STATE_FAILED)
        if on_error:
            try:
                on_error(code, msg)
            except Exception:
                logger.exception("QueryExecutor on_error failed")

    def _prune(self):
        with self._lock:
            self._prune_locked()

    def _prune_locked(self):
        if len(self._requests) > _MAX_REQUESTS:
            completed = [(rid, r) for rid, r in self._requests.items()
                         if r["state"] in (STATE_COMPLETED, STATE_CANCELLED, STATE_FAILED, STATE_STALE)]
            to_remove = len(completed) - _MAX_REQUESTS // 2
            for rid, _ in completed[:to_remove]:
                del self._requests[rid]
