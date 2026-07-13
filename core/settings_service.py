"""SettingsService — agnostic UI service for reading/writing/validating settings.
Transaction lifecycle coordinated by SettingsRuntimeCoordinator:
validate → capture previous → apply service change → persist → emit
"""
from __future__ import annotations

import logging
from typing import Any

from core.settings_schema import ALL_CATEGORIES, get_entry
from core.settings_manager import SETTINGS

logger = logging.getLogger("michi.settings_service")


class SettingsService:
    def __init__(self, coordinator=None):
        self._coordinator = coordinator

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

    def reset_all(self) -> dict:
        if not self._coordinator:
            return {"ok": False, "error_code": "NO_COORDINATOR", "message": "No hay coordinador de runtime"}
        errors = []
        for cat in ALL_CATEGORIES:
            for section in cat.sections:
                for entry in section.entries:
                    result = self._coordinator.execute(entry.key, entry.default)
                    if not result.get("ok"):
                        errors.append(result)
        return {"ok": not errors, "errors": errors}
