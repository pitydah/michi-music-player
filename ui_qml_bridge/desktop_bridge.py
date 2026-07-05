"""DesktopBridge — minimal desktop integration for QML (MPRIS, notifications)."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Slot

logger = logging.getLogger("michi.desktop")


class DesktopBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str, result=dict)
    def showNotification(self, title: str, message: str):
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            if QSystemTrayIcon.isSystemTrayAvailable():
                tray = QSystemTrayIcon()
                tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)
                return {"ok": True}
        except Exception:
            pass
        return {"ok": False, "error": "UNAVAILABLE"}

    @Property(bool, constant=True)
    def systemTrayAvailable(self):
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            return QSystemTrayIcon.isSystemTrayAvailable()
        except Exception:
            return False

    @Property(str, constant=True)
    def desktopEnvironment(self):
        import os
        return os.environ.get("XDG_CURRENT_DESKTOP", os.environ.get("DESKTOP_SESSION", "unknown"))
