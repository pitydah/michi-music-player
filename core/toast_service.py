"""Toast service — unified toast notification API for Michi Music Player.
QML runtime delegates to NotificationBridge.
"""
import logging

logger = logging.getLogger("michi.toast_service")


class ToastService:
    def __init__(self, parent=None, notification_bridge=None):
        self._parent = parent
        self._notif = notification_bridge

    def set_parent(self, parent):
        self._parent = parent

    def set_notification_bridge(self, bridge):
        self._notif = bridge

    def show(self, text: str, level: str = "info", duration: int = None):
        if self._notif and hasattr(self._notif, 'showMessage'):
            return self._notif.showMessage(text, level)
        logger.debug("Toast (no bridge): [%s] %s", level, text)
        return {"ok": True, "level": level, "text": text}

    def info(self, text: str):
        return self.show(text, "info")

    def success(self, text: str):
        return self.show(text, "success")

    def warning(self, text: str):
        return self.show(text, "warning")

    def error(self, text: str):
        return self.show(text, "error")
