"""QueryExecutor — async DB query runner via WorkerManager.run_task, Qt signals for results.

Contract:
    submit(owner, fn, on_success=None, on_error=None) -> request_id
        on_success(result) called on Qt main thread
        on_error(error_code, error_message) called on Qt main thread

    cancel(request_id)
    invalidate(owner)
    is_stale(request_id, owner) -> bool
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.query_executor")

_request_counter = 0
_counter_lock = threading.Lock()

REQUEST_IDLE = "idle"
REQUEST_QUEUED = "queued"
REQUEST_RUNNING = "running"
REQUEST_COMPLETED = "completed"
REQUEST_CANCEL_REQUESTED = "cancel_requested"
REQUEST_CANCELLED = "cancelled"
REQUEST_FAILED = "failed"
REQUEST_STALE = "stale"

ERROR_QUERY_FAILED = "QUERY_FAILED"
ERROR_QUERY_CANCELLED = "QUERY_CANCELLED"
ERROR_QUERY_STALE = "QUERY_STALE"
ERROR_SQLITE_THREAD = "SQLITE_THREAD_ERROR"
ERROR_NO_WORKER = "NO_WORKER_MANAGER"


def _next_request_id() -> int:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


class QueryExecutor(QObject):
    success = Signal(int, object)
    failure = Signal(int, str, str)

    def __init__(self, worker_manager=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._requests: dict[int, dict] = {}
        self._generations: dict[str, int] = {}
        self._lock = threading.Lock()

    def submit(self, owner: str, callable_fn: Callable,
               on_success: Callable | None = None,
               on_error: Callable | None = None,
               request_context: dict | None = None) -> int:
        request_id = _next_request_id()

        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            self._requests[request_id] = {
                "request_id": request_id,
                "owner": owner,
                "generation": gen,
                "state": REQUEST_QUEUED,
                "context": request_context or {},
            }

        def _run():
            if self._check_cancelled(request_id):
                return None
            with self._update_state(request_id, REQUEST_RUNNING):
                pass
            try:
                result = callable_fn()
                return {"ok": True, "result": result}
            except Exception as e:
                logger.error("QueryExecutor: %s failed: %s", owner, e)
                return {"ok": False, "error": str(e)}

        def _done(task_result):
            if self._check_cancelled(request_id):
                return
            with self._lock:
                req = self._requests.get(request_id)
                if not req:
                    return
                if req["generation"] != self._generations.get(owner):
                    req["state"] = REQUEST_STALE
                    self._failure_emit(request_id, ERROR_QUERY_STALE, "Resultado obsoleto", on_error)
                    return
            if task_result is None:
                req = self._requests.get(request_id)
                if req and req["state"] == REQUEST_CANCEL_REQUESTED:
                    req["state"] = REQUEST_CANCELLED
                    self._failure_emit(request_id, ERROR_QUERY_CANCELLED, "Consulta cancelada", on_error)
                else:
                    req["state"] = REQUEST_FAILED
                    self._failure_emit(request_id, ERROR_QUERY_FAILED, "Error de consulta", on_error)
                return
            if not task_result.get("ok"):
                req = self._requests.get(request_id)
                if req:
                    req["state"] = REQUEST_FAILED
                err_msg = task_result.get("error", "Error desconocido")
                self._failure_emit(request_id, ERROR_QUERY_FAILED, err_msg, on_error)
                return
            with self._lock:
                req = self._requests.get(request_id)
                if req:
                    req["state"] = REQUEST_COMPLETED
            result = task_result["result"]
            self.success.emit(request_id, result)
            if on_success:
                try:
                    on_success(result)
                except Exception:
                    logger.exception("QueryExecutor on_success failed")

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(f"qe_{request_id}", _run, on_done=_done)
        else:
            result = _run()
            _done(result)

        return request_id

    def cancel(self, request_id: int):
        with self._lock:
            req = self._requests.get(request_id)
            if req and req["state"] in (REQUEST_QUEUED, REQUEST_RUNNING):
                req["state"] = REQUEST_CANCEL_REQUESTED

    def invalidate(self, owner: str):
        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            stale = [rid for rid, req in self._requests.items()
                     if req.get("owner") == owner]
            for rid in stale:
                req = self._requests[rid]
                if req["state"] in (REQUEST_QUEUED, REQUEST_RUNNING):
                    req["state"] = REQUEST_CANCELLED

    def is_stale(self, request_id: int, owner: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return True
            return req.get("generation", 0) != self._generations.get(owner, 0)

    def _check_cancelled(self, request_id: int) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            return req is not None and req["state"] == REQUEST_CANCEL_REQUESTED

    def _update_state(self, request_id: int, new_state: str):
        class _Ctx:
            def __enter__(s):
                pass
            def __exit__(s, *a):
                with self._lock:
                    req = self._requests.get(request_id)
                    if req:
                        req["state"] = new_state
        return _Ctx()

    def _failure_emit(self, request_id: int, code: str, msg: str, on_error: Callable | None):
        self.failure.emit(request_id, code, msg)
        if on_error:
            try:
                on_error(code, msg)
            except Exception:
                logger.exception("QueryExecutor on_error failed")
