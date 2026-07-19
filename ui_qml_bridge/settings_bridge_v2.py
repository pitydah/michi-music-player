"""SettingsBridgeV2 — transactional QML bridge for SettingsService.

Values are still applied immediately to the runtime service, but every first
change records its previous value.  QML can therefore expose a reliable dirty
state, commit the current values, or roll the complete editing session back.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.settings_schema import get_entry
from core.settings_service import SettingsService


class SettingsBridgeV2(QObject):
    dataChanged = Signal()
    pendingChanged = Signal()

    def __init__(self, service: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = service
        self._pending_changes: dict[str, dict] = {}

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._svc.categories()

    @Property(bool, notify=pendingChanged)
    def hasPendingChanges(self) -> bool:
        return bool(self._pending_changes)

    @Property(int, notify=pendingChanged)
    def pendingCount(self) -> int:
        return len(self._pending_changes)

    def _emit_changes(self) -> None:
        self.dataChanged.emit()
        self.pendingChanged.emit()

    def _track_successful_change(self, key: str, previous, current) -> None:
        if key not in self._pending_changes:
            self._pending_changes[key] = {
                "previous": previous,
                "value": current,
            }
        else:
            self._pending_changes[key]["value"] = current

        # Returning to the original value means the setting is no longer dirty.
        if current == self._pending_changes[key].get("previous"):
            self._pending_changes.pop(key, None)

    @Slot(str, result="QVariant")
    def getValue(self, key: str):
        return self._svc.get(key)

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key: str, value):
        previous = self._svc.get(key)
        result = self._svc.set_(key, value)
        if result.get("ok"):
            current = self._svc.get(key)
            self._track_successful_change(key, previous, current)
        self._emit_changes()
        return result

    @Slot(str, result=dict)
    def resetValue(self, key: str):
        previous = self._svc.get(key)
        result = self._svc.reset(key)
        if result.get("ok"):
            current = self._svc.get(key)
            self._track_successful_change(key, previous, current)
        self._emit_changes()
        return result

    def _all_schema_keys(self) -> list[str]:
        keys: list[str] = []
        for category in self._svc.categories() or []:
            for section in category.get("sections", []) or []:
                for entry in section.get("entries", []) or []:
                    key = entry.get("key")
                    if key:
                        keys.append(key)
        return keys

    @Slot(result=dict)
    def resetAll(self):
        keys = self._all_schema_keys()
        before = {key: self._svc.get(key) for key in keys}
        result = self._svc.reset_all()
        if result.get("ok"):
            for key in keys:
                self._track_successful_change(key, before[key], self._svc.get(key))
        self._emit_changes()
        return result

    @Slot(str, result=dict)
    def validate(self, key: str):
        entry = get_entry(key)
        if not entry:
            return {"ok": False, "valid": False, "error": "UNKNOWN_KEY"}
        return {"ok": True, "valid": True, "key": key, "type": entry.entry_type}

    @Slot(result=dict)
    def pending(self):
        return {
            "ok": True,
            "pending": [
                {
                    "key": key,
                    "value": change.get("value"),
                    "previous": change.get("previous"),
                }
                for key, change in self._pending_changes.items()
            ],
        }

    @Slot(str, "QVariant", result=dict)
    def apply(self, key: str, value):
        return self.setValue(key, value)

    @Slot(str, result=dict)
    def commit(self, key: str):
        existed = key in self._pending_changes
        self._pending_changes.pop(key, None)
        self._emit_changes()
        return {"ok": True, "committed": key, "existed": existed}

    @Slot(result=dict)
    def commitAll(self):
        count = len(self._pending_changes)
        self._pending_changes.clear()
        self._emit_changes()
        return {"ok": True, "committed": count}

    @Slot(str, result=dict)
    def rollback(self, key: str):
        change = self._pending_changes.get(key)
        if change is None:
            return {"ok": False, "error": "NO_PENDING_CHANGE"}
        result = self._svc.set_(key, change.get("previous"))
        if result.get("ok"):
            self._pending_changes.pop(key, None)
        self._emit_changes()
        return result

    @Slot(result=dict)
    def rollbackAll(self):
        restored = 0
        failures: list[dict] = []
        # Reverse insertion order so dependent settings unwind predictably.
        for key in reversed(list(self._pending_changes.keys())):
            change = self._pending_changes[key]
            result = self._svc.set_(key, change.get("previous"))
            if result.get("ok"):
                restored += 1
                self._pending_changes.pop(key, None)
            else:
                failures.append({"key": key, "result": result})
        self._emit_changes()
        return {
            "ok": not failures,
            "restored": restored,
            "failures": failures,
        }

    @Slot(str, result=dict)
    def reject(self, key: str):
        # A rejected immediate edit must restore its persisted/runtime value.
        return self.rollback(key)

    @Slot()
    def refresh(self):
        self._emit_changes()
