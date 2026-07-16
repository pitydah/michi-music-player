"""NotificationActionService — route notification actions."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.notification_action")


class NotificationActionService:
    def __init__(self, navigation_service=None):
        self._nav = navigation_service

    def route(self, action: str, payload: dict | None = None) -> dict:
        targets = {
            "open_settings": "settings",
            "open_diagnostics": "diagnostics",
            "open_job": "jobs",
            "open_track": "library",
            "open_device": "devices.list",
            "retry": "",
            "undo": "",
        }
        route = targets.get(action, "")
        if route and self._nav:
            self._nav.navigate(route)
            return {"ok": True, "route": route}
        return {"ok": True, "action": action}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
