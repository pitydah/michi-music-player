"""NavigationService — route management, history, deep links."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.navigation")


class NavigationService:
    def __init__(self):
        self._history: list[str] = []
        self._max_history = 50

    def navigate(self, route: str) -> dict:
        self._history.append(route)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        return {"ok": True, "route": route}

    def back(self) -> dict:
        if len(self._history) > 1:
            self._history.pop()
            return {"ok": True, "route": self._history[-1] if self._history else "home"}
        return {"ok": False, "error": "NO_HISTORY"}

    def history(self) -> list[str]:
        return list(self._history)

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        self._history.clear()
