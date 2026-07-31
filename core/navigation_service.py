"""NavigationService — UI-agnostic navigation request service.

Emits navigation requests that a UI bridge (NavigationBridge) can consume via
:meth:`subscribe` (push model). This replaces the former bridge-side polling.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class NavigationService:
    def __init__(self):
        self._last_request: dict[str, Any] | None = None
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    def subscribe(self, listener: Callable[[dict[str, Any]], None]) -> None:
        """Register a listener invoked on each navigation request (push).

        A UI bridge subscribes once at construction instead of polling
        ``pop_last_request`` on a timer.
        """
        if callable(listener) and listener not in self._listeners:
            self._listeners.append(listener)

    def navigate(self, route: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._last_request = {"route": route, "params": params or {}}
        self._notify(self._last_request)
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "route": route}

    def go_back(self) -> dict[str, Any]:
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "action": "back"}

    def go_forward(self) -> dict[str, Any]:
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "action": "forward"}

    def _notify(self, request: dict[str, Any]) -> None:
        """Push a request to every subscribed listener (best-effort)."""
        for listener in list(self._listeners):
            try:
                listener(request)
            except Exception:
                logger.debug("Navigation listener raised", exc_info=True)

    def peek_last_request(self) -> dict[str, Any] | None:
        return self._last_request

    def current_route(self) -> str | None:
        if self._last_request:
            return self._last_request["route"]
        return None

    def pop_last_request(self) -> dict[str, Any] | None:
        r = self._last_request
        self._last_request = None
        return r
