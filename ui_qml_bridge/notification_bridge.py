"""NotificationBridge — lightweight toast/notification system for QML workflows."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class NotificationBridge(QObject):
    notificationChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._message = ""
        self._kind = "info"  # info, success, warning, error
        self._visible = False

    @Property(str, notify=notificationChanged)
    def message(self):
        return self._message

    @Property(str, notify=notificationChanged)
    def kind(self):
        return self._kind

    @Property(bool, notify=notificationChanged)
    def visible(self):
        return self._visible

    @Slot(str, str)
    def showMessage(self, text: str, kind: str = "info"):
        self._message = text
        self._kind = kind if kind in ("info", "success", "warning", "error") else "info"
        self._visible = True
        self.notificationChanged.emit()

    @Slot()
    def clear(self):
        self._message = ""
        self._kind = "info"
        self._visible = False
        self.notificationChanged.emit()
