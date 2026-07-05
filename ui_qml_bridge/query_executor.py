"""QueryExecutor — async database query runner via WorkerManager.

Dispatches queries to background thread, returns results via signals.
Handles stale responses, cancellation, and request generation.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.query_executor")

_request_counter = 0
_counter_lock = threading.Lock()


def _next_request_id() -> int:
    global _request_counter
    with _counter_lock:
        _request_counter += 1
        return _request_counter


class QueryExecutor(QObject):
    """Executes database queries asynchronously via WorkerManager."""

    success = Signal(int, object)  # request_id, result
    failure = Signal(int, str)     # request_id, error_message
    progress = Signal(int, float)  # request_id, progress_0_1

    def __init__(self, worker_manager=None, parent=None):
        super().__init__(parent)
        self._wm = worker_manager
        self._active_requests: dict[int, dict] = {}
        self._generations: dict[str, int] = {}

    def submit(self, owner: str, callable_fn: Callable,
               request_context: dict | None = None) -> int:
        """Submit a query for async execution. Returns request_id."""
        request_id = _next_request_id()
        gen = self._generations.get(owner, 0) + 1
        self._generations[owner] = gen
        self._active_requests[request_id] = {
            "owner": owner,
            "generation": gen,
            "context": request_context or {},
        }

        def _run():
            try:
                result = callable_fn()
                return result
            except Exception as e:
                logger.error("QueryExecutor: %s failed: %s", owner, e)
                return None

        def _done(result):
            if request_id not in self._active_requests:
                return  # cancelled
            req = self._active_requests.pop(request_id, {})
            if req.get("generation") != self._generations.get(owner):
                return  # stale
            if result is not None:
                self.success.emit(request_id, result)
            else:
                self.failure.emit(request_id, "Query failed")

        if self._wm and hasattr(self._wm, 'run'):
            self._wm.run(_run, callback=_done)
        else:
            # Fallback synchronous
            result = _run()
            _done(result)

        return request_id

    def cancel(self, request_id: int):
        """Cancel a pending request. No-op if already completed."""
        self._active_requests.pop(request_id, None)

    def invalidate(self, owner: str):
        """Invalidate all requests for a given owner."""
        gen = self._generations.get(owner, 0) + 1
        self._generations[owner] = gen
        stale = [rid for rid, req in self._active_requests.items()
                 if req.get("owner") == owner]
        for rid in stale:
            self._active_requests.pop(rid, None)

    def is_stale(self, request_id: int, owner: str) -> bool:
        req = self._active_requests.get(request_id)
        if not req:
            return True
        return req.get("generation", 0) != self._generations.get(owner, 0)
