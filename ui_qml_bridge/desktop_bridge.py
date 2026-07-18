"""DesktopBridge — minimal desktop integration for QML (notifications, MPRIS).
Uses DBus for notifications instead of QSystemTrayIcon.
"""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Property, Slot

logger = logging.getLogger("michi.desktop")


class DesktopBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str, result=dict)
    def showNotification(self, title: str, message: str):
        try:
            import subprocess
            subprocess.run(["notify-send", title, message], capture_output=True, timeout=5)
            return {"ok": True}
        except Exception:
            pass
        return {"ok": False, "error": "UNAVAILABLE"}

    @Property(bool, constant=True)
    def systemTrayAvailable(self):
        try:
            import subprocess
            r = subprocess.run(["which", "notify-send"], capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    @Property(str, constant=True)
    def desktopEnvironment(self):
        return os.environ.get("XDG_CURRENT_DESKTOP", os.environ.get("DESKTOP_SESSION", "unknown"))
