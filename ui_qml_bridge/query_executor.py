"""QueryExecutor — async DB query runner using WorkerManager TaskHandle.

No deadlocks. Terminal cancellation semantics. Does not own WorkerManager.
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


def _next_id() -> int:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


def _terminal_failure(request_id: int, code: str) -> dict:
    return {"request_id": request_id, "ok": False, "error": code, "message": ""}


class QueryExecutor(QObject):
    success = Signal(int, object)
    failure = Signal(int, str, str)
    requestStateChanged = Signal(int, str)
    requestFinished = Signal(int)

    def __init__(self, worker_manager=None, parent=None, owns_worker_manager=False):
        super().__init__(parent)
        self._wm = worker_manager
        self._owns_wm = owns_worker_manager
        self._requests: dict[int, dict] = {}
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

        with self._lock:
            if self._shutdown:
                req = {
                    "request_id": request_id, "owner": owner,
                    "generation": 0, "state": STATE_SHUTDOWN,
                    "context": request_context or {},
                }
                self._requests[request_id] = req
                self._prune_locked()
        if self._shutdown:
            self.failure.emit(request_id, ERR_QUERY_SHUTDOWN, "QueryExecutor en shutdown")
            self.requestStateChanged.emit(request_id, STATE_SHUTDOWN)
            self.requestFinished.emit(request_id)
            if on_error:
                on_error(ERR_QUERY_SHUTDOWN, "QueryExecutor en shutdown")
            return request_id

        with self._lock:
            gen = self._generations.get(owner, 0) + 1
            self._generations[owner] = gen
            if supersede:
                stale = [rid for rid, r in self._requests.items()
                         if r.get("owner") == owner
                         and r["state"] in (STATE_QUEUED, STATE_RUNNING)]
                for rid in stale:
                    r = self._requests[rid]
                    r["state"] = STATE_CANCEL_REQUESTED
                    if self._wm and hasattr(self._wm, 'cancel_task'):
                        self._wm.cancel_task(f"qe_{rid}")
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
                if not req or req["state"] in (STATE_CANCELLED, STATE_CANCEL_REQUESTED, STATE_SHUTDOWN):
                    return {"ok": False, "error": ERR_QUERY_CANCELLED}
                req["state"] = STATE_RUNNING
            try:
                result = callable_fn()
                return {"ok": True, "result": result}
            except Exception as e:
                logger.error("QueryExecutor: %s failed: %s", owner, e)
                code = self._map_sqlite_error(e)
                return {"ok": False, "error": code, "message": str(e)}

        def _on_done(task_result):
            if self._shutdown:
                return
            req = None
            state = STATE_COMPLETED
            code = ""
            msg = ""
            result = None

            with self._lock:
                req = self._requests.get(request_id)
                if not req:
                    return
                if req["generation"] != self._generations.get(owner):
                    req["state"] = STATE_STALE
                    self._prune_locked()
                    state = STATE_STALE
                    code = ERR_QUERY_STALE
                    msg = "Resultado obsoleto"
                elif not task_result or not task_result.get("ok"):
                    code = task_result.get("error", ERR_QUERY_FAILED) if task_result else ERR_QUERY_CANCELLED
                    msg = task_result.get("message", "") if task_result else "Cancelado"
                    req["state"] = STATE_CANCELLED if code == ERR_QUERY_CANCELLED else STATE_FAILED
                else:
                    req["state"] = STATE_COMPLETED
                    result = task_result["result"]
                    self._requests[request_id]["state"] = STATE_COMPLETED

            if state == STATE_STALE:
                self.failure.emit(request_id, code, msg)
                self.requestStateChanged.emit(request_id, STATE_STALE)
                self.requestFinished.emit(request_id)
                if on_error:
                    on_error(code, msg)
                return
            if not task_result or not task_result.get("ok"):
                self.failure.emit(request_id, code, msg)
                final_state = STATE_CANCELLED if code == ERR_QUERY_CANCELLED else STATE_FAILED
                self.requestStateChanged.emit(request_id, final_state)
                self.requestFinished.emit(request_id)
                if code == ERR_QUERY_CANCELLED and on_cancelled:
                    on_cancelled()
                elif on_error:
                    on_error(code, msg)
                self._prune()
                return

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
                on_cancelled=on_cancelled,
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
                if self._wm and hasattr(self._wm, 'cancel_task'):
                    self._wm.cancel_task(f"qe_{request_id}")
        self.requestStateChanged.emit(request_id, STATE_CANCEL_REQUESTED)

    def cancel_owner(self, owner: str):
        with self._lock:
            targets = [rid for rid, r in self._requests.items()
                       if r.get("owner") == owner
                       and r["state"] in (STATE_QUEUED, STATE_RUNNING)]
        for rid in targets:
            if self._wm and hasattr(self._wm, 'cancel_task'):
                self._wm.cancel_task(f"qe_{rid}")
                self.requestStateChanged.emit(rid, STATE_CANCEL_REQUESTED)

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

    def request_context(self, request_id: int) -> dict:
        with self._lock:
            req = self._requests.get(request_id)
            return dict(req.get("context", {})) if req else {}

    def active_requests(self, owner: str = "") -> list[int]:
        with self._lock:
            return [rid for rid, r in self._requests.items()
                    if (not owner or r.get("owner") == owner)
                    and r["state"] in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]

    def completed_requests(self, owner: str = "") -> list[int]:
        with self._lock:
            return [rid for rid, r in self._requests.items()
                    if r["state"] == STATE_COMPLETED
                    and (not owner or r.get("owner") == owner)]

    def shutdown(self, timeout_ms: int = 2000):
        self._shutdown = True
        with self._lock:
            targets = [rid for rid, r in self._requests.items()
                       if r["state"] in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]
        for rid in targets:
            self.cancel(rid)
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
                          if r["state"] in (STATE_QUEUED, STATE_RUNNING, STATE_CANCEL_REQUESTED)]
                if not active:
                    return True
            time.sleep(0.05)
        return False

    # ── Internal ──

    def _prune(self):
        with self._lock:
            self._prune_locked()

    def _prune_locked(self):
        if len(self._requests) > _MAX_REQUESTS:
            completed = [(rid, r) for rid, r in self._requests.items()
                         if r["state"] in (STATE_COMPLETED, STATE_CANCELLED,
                                           STATE_FAILED, STATE_STALE, STATE_SHUTDOWN)]
            to_remove = len(completed) - _MAX_REQUESTS // 2
            for rid, _ in completed[:to_remove]:
                del self._requests[rid]

    def _map_sqlite_error(self, exc: Exception) -> str:
        msg = str(exc)
        if isinstance(exc, self._sqlite_error_types()):
            if "busy" in msg.lower():
                return ERR_SQLITE_BUSY
            if "locked" in msg.lower():
                return ERR_SQLITE_LOCKED
            if "readonly" in msg.lower():
                return ERR_SQLITE_READONLY
            if "corrupt" in msg.lower():
                return ERR_SQLITE_CORRUPT
            if "no such table" in msg.lower() or "no such column" in msg.lower():
                return ERR_INVALID_QUERY
            return ERR_QUERY_FAILED
        return ERR_QUERY_FAILED

    @staticmethod
    def _sqlite_error_types():
        try:
            import sqlite3
            return (sqlite3.DatabaseError,)
        except ImportError:
            return (Exception,)
