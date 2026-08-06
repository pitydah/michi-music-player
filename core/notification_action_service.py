"""NotificationActionService — canonical notification action dispatch.

Every action id maps to a real dispatch branch that executes the requested
effect: retry re-runs the ORIGINAL durable job payload, undo runs a real
compensation through UndoService, open_* routes through NavigationService.
Unknown ids return ACTION_NOT_FOUND; unwired services return
CAPABILITY_UNAVAILABLE or TARGET_UNAVAILABLE. There is no
``{"ok": True, "action": ...}`` without execution.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("michi.notification_action")


class NotificationActionService:
    def __init__(self, navigation_service=None, job_service=None,
                 undo_service=None, notification_service=None,
                 service_locator: Callable[[str], Any] | None = None):
        self._nav = navigation_service
        self._js = job_service
        self._undo = undo_service
        self._ns = notification_service
        self._locator = service_locator

    def _resolve(self, name: str, current):
        if current is not None:
            return current
        if self._locator is not None:
            try:
                return self._locator(name)
            except Exception:  # noqa: BLE001
                return None
        return None

    def route(self, action: str, payload: dict | None = None) -> dict:
        """Dispatch a notification action to its real handler."""
        dispatch: dict[str, Callable[[dict], dict]] = {
            "retry": self._retry,
            "undo": self._undo_action,
            "open_job": self._open_job,
            "open_track": self._open_track,
            "open_settings": self._open_settings,
            "open_diagnostics": self._open_diagnostics,
            "open_device": self._open_device,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {
                "ok": False,
                "status": "ACTION_NOT_FOUND",
                "code": "ACTION_NOT_FOUND",
                "action": action,
                "message": f"No dispatch branch for action '{action}'",
            }
        return handler(payload or {})

    def dispatch_ids(self) -> list[str]:
        return ["retry", "undo", "open_job", "open_track", "open_settings",
                "open_diagnostics", "open_device"]

    # ── retry: re-run the ORIGINAL durable job (payload preserved) ───────

    def _retry(self, payload: dict) -> dict:
        job_id = str(payload.get("job_id", "") or "")
        if not job_id:
            return {"ok": False, "status": "TARGET_UNAVAILABLE",
                    "code": "TARGET_UNAVAILABLE",
                    "message": "Notification has no job_id to retry"}
        job_service = self._resolve("job_service", self._js)
        if job_service is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "JobService unavailable"}
        job = job_service.get_job(job_id)
        if job is None:
            return {"ok": False, "status": "ACTION_NOT_FOUND",
                    "code": "ACTION_NOT_FOUND",
                    "message": f"Job {job_id} no longer exists"}
        if not job.retryable:
            return {"ok": False, "status": "NOT_RETRYABLE",
                    "code": "NOT_RETRYABLE",
                    "message": f"Job {job_id} is not retryable"}
        if not job_service.retry_job(job_id):
            return {"ok": False, "status": "NOT_RETRYABLE",
                    "code": "NOT_RETRYABLE",
                    "message": f"Job {job_id} cannot be re-queued"}
        started = job_service.start_job(job_id) or job_service.process_queue() > 0
        state = "RUNNING" if started else "QUEUED"
        return {
            "ok": True,
            "status": state,
            "code": "RETRY_QUEUED",
            "job_id": job_id,
            "message": f"Job {job_id} re-queued with original payload",
            "payload_preserved": True,
        }

    # ── undo: real compensation through UndoService ──────────────────────

    def _undo_action(self, payload: dict) -> dict:
        operation_id = str(payload.get("operation_id", "") or "")
        if not operation_id:
            return {"ok": False, "status": "TARGET_UNAVAILABLE",
                    "code": "TARGET_UNAVAILABLE",
                    "message": "Notification carries no operation_id to undo"}
        undo_service = self._resolve("undo_service", self._undo)
        if undo_service is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "UndoService unavailable"}
        result = undo_service.undo(operation_id)
        if not result.ok:
            return {"ok": False, "status": result.code,
                    "code": result.code,
                    "message": result.message,
                    "operation_id": operation_id}
        return {"ok": True, "status": "UNDONE",
                "code": "UNDO_COMPLETED",
                "operation_id": operation_id,
                "message": f"Operación {operation_id} revertida",
                "description": result.data.get("description", "")}

    # ── navigation-based actions ─────────────────────────────────────────

    def _open_job(self, payload: dict) -> dict:
        job_id = str(payload.get("job_id", "") or "")
        nav = self._resolve("navigation_service", self._nav)
        if nav is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "NavigationService unavailable"}
        params = {"job_id": job_id} if job_id else {}
        result = nav.navigate("jobs", params)
        return {"ok": bool(result.get("ok")), "status": "NAVIGATION_REQUESTED",
                "code": "NAVIGATION_REQUESTED", "route": "jobs",
                "params": params}

    def _open_track(self, payload: dict) -> dict:
        nav = self._resolve("navigation_service", self._nav)
        if nav is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "NavigationService unavailable"}
        entity = str(payload.get("entity", "") or "")
        params = {"track_id": entity.replace("track_", "")} if entity else {}
        result = nav.navigate("library", params)
        return {"ok": bool(result.get("ok")), "status": "NAVIGATION_REQUESTED",
                "code": "NAVIGATION_REQUESTED", "route": "library",
                "params": params}

    def _open_settings(self, payload: dict) -> dict:
        nav = self._resolve("navigation_service", self._nav)
        if nav is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "NavigationService unavailable"}
        result = nav.navigate("settings")
        return {"ok": bool(result.get("ok")), "status": "NAVIGATION_REQUESTED",
                "code": "NAVIGATION_REQUESTED", "route": "settings"}

    def _open_diagnostics(self, payload: dict) -> dict:
        nav = self._resolve("navigation_service", self._nav)
        if nav is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "NavigationService unavailable"}
        result = nav.navigate("diagnostics")
        return {"ok": bool(result.get("ok")), "status": "NAVIGATION_REQUESTED",
                "code": "NAVIGATION_REQUESTED", "route": "diagnostics"}

    def _open_device(self, payload: dict) -> dict:
        nav = self._resolve("navigation_service", self._nav)
        if nav is None:
            return {"ok": False, "status": "CAPABILITY_UNAVAILABLE",
                    "code": "CAPABILITY_UNAVAILABLE",
                    "message": "NavigationService unavailable"}
        result = nav.navigate("devices.list")
        return {"ok": bool(result.get("ok")), "status": "NAVIGATION_REQUESTED",
                "code": "NAVIGATION_REQUESTED", "route": "devices.list"}

    def health(self) -> dict:
        return {
            "available": True,
            "dispatch_ids": self.dispatch_ids(),
            "navigation_available": self._nav is not None
            or self._locator is not None,
            "job_service_available": self._js is not None
            or self._locator is not None,
            "undo_service_available": self._undo is not None
            or self._locator is not None,
        }

    def shutdown(self):
        pass
