"""SettingsBridgeV2 — transactional QML bridge for SettingsService.

Values are still applied immediately to the runtime service, but every first
change records its previous value.  QML can therefore expose a reliable dirty
state, commit the current values, or roll the complete editing session back.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.secrets import is_sensitive
from core.settings_manager import SETTINGS
from core.settings_schema import get_entry
from core.settings_service import SettingsService


class SettingsBridgeV2(QObject):
    dataChanged = Signal()
    pendingChanged = Signal()

    def __init__(self, service: SettingsService, settings=None, parent=None):
        super().__init__(parent)
        self._svc = service
        self._settings = settings or SETTINGS
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

    def _track_successful_change(self, key: str, previous, current, existed: bool) -> None:
        if key not in self._pending_changes:
            self._pending_changes[key] = {
                "previous": previous,
                "value": current,
                "existed": existed,
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
        existed = bool(self._settings.contains(key))
        result = self._svc.set_(key, value)
        if result.get("ok"):
            current = self._svc.get(key)
            self._track_successful_change(key, previous, current, existed)
        self._emit_changes()
        return result

    @Slot(str, result=dict)
    def resetValue(self, key: str):
        previous = self._svc.get(key)
        existed = bool(self._settings.contains(key))
        result = self._svc.reset(key)
        if result.get("ok"):
            current = self._svc.get(key)
            self._track_successful_change(key, previous, current, existed)
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
        changed: list[str] = []
        failed: list[dict] = []
        for key in keys:
            previous = self._svc.get(key)
            existed = bool(self._settings.contains(key))
            result = self._svc.reset(key)
            if result.get("ok"):
                current = self._svc.get(key)
                self._track_successful_change(key, previous, current, existed)
                if current != previous:
                    changed.append(key)
            else:
                failed.append({"key": key, "result": result})
        self._emit_changes()
        return {"ok": not failed, "changed": changed, "failed": failed}

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
                    "value": "<redacted>" if is_sensitive(key) else change.get("value"),
                    "previous": "<redacted>" if is_sensitive(key) else change.get("previous"),
                }
                for key, change in self._pending_changes.items()
            ],
        }

    @Slot(str, "QVariant", result=dict)
    def apply(self, key: str, value):
        return self.setValue(key, value)

    @Slot(str, result=dict)
    def commit(self, key: str):
        if key not in self._pending_changes:
            return {"ok": False, "changed": [], "failed": [{"key": key, "error": "NO_PENDING_CHANGE"}]}
        failure = self._sync_failure(key)
        if failure:
            return {"ok": False, "changed": [], "failed": [failure]}
        self._pending_changes.pop(key)
        self._emit_changes()
        return {"ok": True, "changed": [key], "failed": []}

    @Slot(result=dict)
    def commitAll(self):
        changed = list(self._pending_changes)
        if not changed:
            return {"ok": True, "changed": [], "failed": []}
        failure = self._sync_failure("")
        if failure:
            return {"ok": False, "changed": [], "failed": [failure]}
        self._pending_changes.clear()
        self._emit_changes()
        return {"ok": True, "changed": changed, "failed": []}

    def _sync_failure(self, key: str) -> dict | None:
        try:
            self._settings.sync()
            status = self._settings.status()
        except (AttributeError, RuntimeError) as exc:
            return {"key": key, "error": "SETTINGS_SYNC_FAILED", "message": str(exc)}
        raw_status = getattr(status, "value", status)
        status_code = raw_status if isinstance(raw_status, int) else 0
        if status_code != 0:
            return {"key": key, "error": "SETTINGS_SYNC_FAILED", "status": status_code}
        return None

    def _restore(self, key: str, change: dict) -> dict:
        result = self._svc.set_(key, change.get("previous"))
        if not result.get("ok"):
            return result
        if not change.get("existed", True):
            self._settings.remove(key)
        failure = self._sync_failure(key)
        if failure:
            return {"ok": False, **failure}
        return result

    @Slot(str, result=dict)
    def rollback(self, key: str):
        change = self._pending_changes.get(key)
        if change is None:
            return {"ok": False, "error": "NO_PENDING_CHANGE"}
        result = self._restore(key, change)
        if result.get("ok"):
            self._pending_changes.pop(key, None)
        self._emit_changes()
        return result

    @Slot(result=dict)
    def rollbackAll(self):
        changed: list[str] = []
        failed: list[dict] = []
        # Reverse insertion order so dependent settings unwind predictably.
        for key in reversed(list(self._pending_changes.keys())):
            change = self._pending_changes[key]
            result = self._restore(key, change)
            if result.get("ok"):
                changed.append(key)
                self._pending_changes.pop(key, None)
            else:
                failed.append({"key": key, "result": result})
        self._emit_changes()
        return {
            "ok": not failed,
            "changed": changed,
            "failed": failed,
        }

    @Slot(str, result=dict)
    def reject(self, key: str):
        # A rejected immediate edit must restore its persisted/runtime value.
        return self.rollback(key)

    @Slot()
    def refresh(self):
        self._emit_changes()
