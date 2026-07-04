"""DiagnosticsBridge — QML diagnostics and health checks."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import sys
import platform


class DiagnosticsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, service_registry=None, parent=None):
        super().__init__(parent)
        self._registry = service_registry

    @Slot(result="QVariantMap")
    def runQuickCheck(self):
        result = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "qml_mode": True,
            "app_version": "0.2.0a0",
        }
        if self._registry:
            result["player_available"] = self._registry.isAvailable("player_service")
            result["db_available"] = self._registry.isAvailable("db")
            result["radio_available"] = self._registry.isAvailable("radio_manager")
            result["sync_available"] = self._registry.isAvailable("sync_manager")
        else:
            for key in ("player_available", "db_available", "radio_available", "sync_available"):
                result[key] = False
        return result

    @Property("QVariantList", notify=dataChanged)
    def checks(self):
        check = self.runQuickCheck()
        items = []
        for key, value in check.items():
            items.append({"key": key, "value": str(value), "ok": bool(value) if isinstance(value, (bool, int)) else True})
        return items

    @Slot(result=str)
    def copyDiagnostics(self):
        items = self.checks
        lines = ["=== Michi Music Player Diagnostics ==="]
        for item in items:
            status = "OK" if item["ok"] else "FAIL"
            lines.append(f"  {status}  {item['key']}: {item['value']}")
        return "\n".join(lines)

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
