"""SettingsBridgeV2 — QML bridge for SettingsService, replaces legacy SettingsBridge."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.settings_service import SettingsService


class SettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, service: SettingsService | None = None, parent=None):
        super().__init__(parent)
        self._svc = service or SettingsService()

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

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
