"""NavigationService — UI-agnostic navigation request service.

Emits navigation requests that a UI bridge (NavigationBridge) can consume via
:meth:`subscribe` (push model). This replaces the former bridge-side polling.
"""
from __future__ import annotations

import contextlib
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

    def unsubscribe(self, listener: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered listener (no-op if absent).

        Mirrors :meth:`subscribe` so a bridge can cleanly detach during
        teardown instead of being leaked across service rebuilds.
        """
        with contextlib.suppress(ValueError):
            self._listeners.remove(listener)

    def navigate(self, route: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._last_request = {"route": route, "params": params or {}}
        self._notify(self._last_request)
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "route": route}

    def go_back(self) -> dict[str, Any]:
        """Request backward navigation, pushed to listeners like :meth:`navigate`.

        The request carries ``action="back"`` so the bridge can dispatch to its
        own history stack. The last request's route is preserved so
        :meth:`current_route` remains meaningful after the call.
        """
        request = {
            "route": self.current_route() or "",
            "params": {},
            "action": "back",
        }
        self._last_request = request
        self._notify(request)
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "action": "back"}

    def go_forward(self) -> dict[str, Any]:
        """Request forward navigation, pushed to listeners like :meth:`navigate`."""
        request = {
            "route": self.current_route() or "",
            "params": {},
            "action": "forward",
        }
        self._last_request = request
        self._notify(request)
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
