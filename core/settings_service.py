"""SettingsService — agnostic UI service for reading/writing/validating settings."""
from __future__ import annotations

import logging
from typing import Any

from core.settings_schema import ALL_CATEGORIES, get_entry, validate
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
        entry = get_entry(key)
        if not entry:
            return {"ok": False, "error_code": "UNKNOWN_KEY", "message": "Clave desconocida"}
        ok, msg = validate(key, value)
        if not ok:
            return {"ok": False, "error_code": "INVALID_VALUE", "message": msg}
        SETTINGS.setValue(key, value)
        SETTINGS.sync()
        result = {"ok": True, "key": key, "value": value}
        if self._coordinator:
            apply = self._coordinator.apply(key, value)
            result.update({
                "applied": apply.applied,
                "requires_restart": apply.requires_restart,
                "message": apply.message,
            })
        return result

    def reset(self, key: str) -> dict:
        entry = get_entry(key)
        if not entry:
            return {"ok": False, "error_code": "UNKNOWN_KEY", "message": "Clave desconocida"}
        default = entry.default
        SETTINGS.setValue(key, default)
        SETTINGS.sync()
        result = {"ok": True, "key": key, "value": default}
        if self._coordinator:
            apply = self._coordinator.apply(key, default)
            result.update({
                "applied": apply.applied if apply.ok else False,
                "requires_restart": apply.requires_restart,
                "message": apply.message,
            })
        return result

    def get_all(self) -> dict[str, Any]:
        result = {}
        for cat in ALL_CATEGORIES:
            for section in cat.sections:
                for entry in section.entries:
                    result[entry.key] = self.get(entry.key)
        return result

    def reset_all(self) -> dict:
        for cat in ALL_CATEGORIES:
            for section in cat.sections:
                for entry in section.entries:
                    SETTINGS.setValue(entry.key, entry.default)
        SETTINGS.sync()
        return {"ok": True}
