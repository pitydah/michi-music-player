"""SettingsBridgeV2 — QML bridge for SettingsService with coordinator-backed transactions.

Flow: QML -> bridge -> schema -> runtime adapter -> consumer -> persistence -> verify -> applied/rejected -> rollback.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.settings_service import SettingsService
from core.settings_schema import get_entry


class SettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, service: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = service
        self._pending_changes: dict[str, dict] = {}

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._svc.categories()

    @Slot(str, result="QVariant")
    def getValue(self, key: str):
        return self._svc.get(key)

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key: str, value):
        return self._svc.set_(key, value)

    @Slot(str, result=dict)
    def resetValue(self, key: str):
        return self._svc.reset(key)

    @Slot(result=dict)
    def resetAll(self):
        return self._svc.reset_all()

    @Slot(str, result=dict)
    def validate(self, key: str):
        entry = get_entry(key)
        if not entry:
            return {"ok": False, "valid": False, "error": "UNKNOWN_KEY"}
        return {"ok": True, "valid": True, "key": key, "type": entry.entry_type}

    @Slot(result=dict)
    def pending(self):
        return {"ok": True, "pending": [
            {"key": k, "value": v.get("value"), "previous": v.get("previous")}
            for k, v in self._pending_changes.items()
        ]}

    @Slot(str, "QVariant", result=dict)
    def apply(self, key: str, value):
        prev = self._svc.get(key)
        result = self._svc.set_(key, value)
        if result.get("ok"):
            self._pending_changes[key] = {"value": value, "previous": prev}
        self.dataChanged.emit()
        return result

    @Slot(str, result=dict)
    def reject(self, key: str):
        self._pending_changes.pop(key, None)
        self.dataChanged.emit()
        return {"ok": True, "rejected": key}

    @Slot(str, result=dict)
    def rollback(self, key: str):
        change = self._pending_changes.pop(key, None)
        if change and change.get("previous") is not None:
            result = self._svc.set_(key, change["previous"])
            self.dataChanged.emit()
            return result
        return {"ok": False, "error": "NO_PENDING_CHANGE"}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
