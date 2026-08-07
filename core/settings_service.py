"""SettingsService — agnostic UI service for reading/writing/validating settings.
Transaction lifecycle coordinated by SettingsRuntimeCoordinator:
validate → capture previous → apply service change → persist → emit

``reset_all`` is transactional and compensable: every key is previewed, applied
through the coordinator, and on ANY failure all already-applied keys are rolled
back to their captured previous values (compensation).  A single snapshot
event is emitted per call (``settings.reset_all.completed`` on success,
``settings.reset_all.failed`` after rollback).
"""
from __future__ import annotations

import logging
from typing import Any

from core.settings_schema import ALL_CATEGORIES, get_entry
from core.settings_manager import SETTINGS

logger = logging.getLogger("michi.settings_service")

RESET_COMPLETED = "COMPLETED"
RESET_PARTIAL = "PARTIAL_SUCCESS"
RESET_FAILED = "FAILED"


class SettingsService:
    def __init__(self, coordinator=None, event_bus=None, navigation_service=None):
        self._coordinator = coordinator
        self._event_bus = event_bus
        self._navigation = navigation_service

    def set_navigation_service(self, navigation_service) -> None:
        """Late-bind the navigation service (registered after this service)."""
        self._navigation = navigation_service

    def categories(self) -> list[dict]:
        return [
            {
                "id": c.id, "title": c.title, "icon": c.icon,
                "sections": [
                    {
                        "id": s.id, "title": s.title,
                        "entries": [
                            {
                                "key": e.key, "label": e.label,
                                "type": e.entry_type, "default": e.default,
                                "options": e.options or [],
                                "placeholder": e.placeholder or "",
                                "hint": e.hint or "",
                                "requires_restart": e.requires_restart,
                                "min_value": e.min_value,
                                "max_value": e.max_value,
                            }
                            for e in s.entries
                        ],
                    }
                    for s in c.sections
                ],
            }
            for c in ALL_CATEGORIES
        ]

    def get(self, key: str) -> Any:
        entry = get_entry(key)
        default = entry.default if entry else ""
        return SETTINGS.value(key, default)

    def set_(self, key: str, value: Any) -> dict:
        if not self._coordinator:
            return {"ok": False, "error_code": "NO_COORDINATOR", "message": "No hay coordinador de runtime"}
        return self._coordinator.execute(key, value)

    def reset(self, key: str) -> dict:
        if not self._coordinator:
            return {"ok": False, "error_code": "NO_COORDINATOR", "message": "No hay coordinador de runtime"}
        entry = get_entry(key)
        if not entry:
            return {"ok": False, "error_code": "UNKNOWN_KEY", "message": "Clave desconocida"}
        return self._coordinator.execute(key, entry.default)

    def get_all(self) -> dict[str, Any]:
        result = {}
        for cat in ALL_CATEGORIES:
            for section in cat.sections:
                for entry in section.entries:
                    result[entry.key] = self.get(entry.key)
        return result

    def open(self) -> dict:
        """Request settings navigation through the real navigation service.

        Never returns nominal success: the result mirrors the navigation
        service dispatch (NAVIGATION_REQUESTED) or reports
        NAVIGATION_UNAVAILABLE when no navigation service is wired.
        """
        if self._navigation is None:
            return {
                "ok": False,
                "status": "CAPABILITY_UNAVAILABLE",
                "code": "NAVIGATION_UNAVAILABLE",
                "message": "NavigationService no disponible",
            }
        result = self._navigation.navigate("settings")
        ok = bool(result.get("ok"))
        return {
            "ok": ok,
            "status": "NAVIGATION_REQUESTED" if ok else "FAILED",
            "code": result.get("code", "NAVIGATION_REQUESTED" if ok else "FAILED"),
            "route": result.get("route", "settings"),
            "message": "Solicitud de navegación despachada" if ok else "La navegación fue rechazada",
        }

    def _schema_entries(self) -> list:
        return [
            entry
            for cat in ALL_CATEGORIES
            for section in cat.sections
            for entry in section.entries
        ]

    def _coordinator_ok(self, result: dict) -> bool:
        """A key succeeded when the coordinator applied AND persisted it.

        Persistence is the coordinator contract: ``execute`` either returns
        ``persisted=True`` (after a clean QSettings write + status check) or
        fails.  Runtime readback/verification is performed inside the
        coordinator (adapter ``verify``) and reported as ``applied``.
        """
        return bool(result.get("ok")) and result.get("persisted") is not False

    def reset_all(self) -> dict:
        """Transactional reset of every schema key with compensation.

        Phases: preview (previous value + default + restart flag per key) →
        apply through the coordinator → on ANY failure, roll back every
        already-applied key to its captured previous value (reverse order) →
        single snapshot event.  Result reports applied / restart_required /
        rolled_back / rollback_failed lists and previous+default snapshots.
        """
        if not self._coordinator:
            return {
                "ok": False, "status": RESET_FAILED,
                "error_code": "NO_COORDINATOR",
                "message": "No hay coordinador de runtime",
            }

        preview = [
            {
                "key": e.key,
                "previous": SETTINGS.value(e.key, e.default),
                "default": e.default,
                "requires_restart": e.requires_restart,
            }
            for e in self._schema_entries()
        ]

        applied: list[str] = []
        restart_required: list[str] = []
        failed: list[dict] = []
        errors: list[str] = []
        previous_snapshot: dict[str, Any] = {}
        new_snapshot: dict[str, Any] = {}

        for item in preview:
            key = item["key"]
            previous_snapshot[key] = item["previous"]
            result = self._coordinator.execute(key, item["default"])
            if not self._coordinator_ok(result):
                failed.append({"key": key, **result})
                errors.append(result.get("message") or f"Fallo al restaurar {key}")
                break
            new_snapshot[key] = SETTINGS.value(key, item["default"])
            applied.append(key)
            if result.get("requires_restart") or item["requires_restart"]:
                restart_required.append(key)

        rolled_back: list[str] = []
        rollback_failed: list[dict] = []
        status = RESET_COMPLETED

        if failed:
            status = RESET_FAILED
            for key in reversed(applied):
                rollback = self._coordinator.execute(key, previous_snapshot[key])
                if self._coordinator_ok(rollback):
                    rolled_back.append(key)
                    new_snapshot[key] = SETTINGS.value(key, previous_snapshot[key])
                else:
                    rollback_failed.append({"key": key, **rollback})
            if rollback_failed:
                status = RESET_PARTIAL

        ok = not failed and not rollback_failed

        payload = {
            "status": status,
            "ok": ok,
            "applied": list(applied),
            "restart_required": list(restart_required),
            "rolled_back": list(rolled_back),
            "rollback_failed": list(rollback_failed),
            "failed": list(failed),
            "errors": list(errors),
            "previous": dict(previous_snapshot),
            "new": dict(new_snapshot),
            "count": len(applied),
        }
        if self._event_bus is not None:
            event = "settings.reset_all.completed" if ok else "settings.reset_all.failed"
            self._event_bus.emit(event, payload)

        return {
            "ok": ok,
            "status": status,
            "message": (
                "Todas las preferencias restauradas"
                if status == RESET_COMPLETED
                else "La restauración falló y se compensó parcialmente"
                if status == RESET_PARTIAL
                else "La restauración falló y se compensó"
            ),
            **payload,
        }
