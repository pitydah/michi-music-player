"""NavigationService — UI-agnostic navigation request service.

Emits navigation requests that a UI bridge (NavigationBridge) can consume.
"""
from __future__ import annotations

from typing import Any


class NavigationService:
    def __init__(self):
        self._last_request: dict[str, Any] | None = None

    def navigate(self, route: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._last_request = {"route": route, "params": params or {}}
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "route": route}

    def go_back(self) -> dict[str, Any]:
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "action": "back"}

    def go_forward(self) -> dict[str, Any]:
        return {"ok": True, "code": "NAVIGATION_REQUESTED", "action": "forward"}

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
