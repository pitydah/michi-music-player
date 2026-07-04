"""DiagnosticsBridge — QML diagnostics and health checks."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import sys
import platform


class DiagnosticsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, db=None, radio_manager=None, sync_manager=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._db = db
        self._radio = radio_manager
        self._sync = sync_manager

    @Slot(result="QVariantMap")
    def runQuickCheck(self):
        result = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "qml_mode": True,
            "app_version": "0.2.0a0",
            "player_available": self._player is not None,
            "db_available": self._db is not None,
            "radio_available": self._radio is not None,
            "sync_available": self._sync is not None,
        }
        return result

    @Property("QVariantList", notify=dataChanged)
    def checks(self):
        check = self.runQuickCheck()
        items = []
        for key, value in check.items():
            ok = bool(value) if isinstance(value, (bool, type(None))) else bool(value)
            items.append({"key": key, "value": str(value), "ok": ok})
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
