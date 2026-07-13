"""NotificationBridge — notification queue with priority, dedup, timeout, actions."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import time


class NotificationBridge(QObject):
    notificationChanged = Signal()
    notificationCountChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current: dict | None = None
        self._queue: list[dict] = []
        self._max_queue = 20
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(5000)
        self._timeout_timer.timeout.connect(self._next)

    @Property("QVariant", notify=notificationChanged)
    def currentNotification(self):
        return dict(self._current) if self._current else None

    @Property(int, notify=notificationCountChanged)
    def queueLength(self):
        return len(self._queue)

    @Slot(str, str, result=dict)
    def showMessage(self, text: str, kind: str = "info"):
        msg = {
            "id": int(time.time() * 1000),
            "text": text,
            "kind": kind if kind in ("info", "success", "warning", "error") else "info",
            "timestamp": time.time(),
            "action": "",
            "persistent": kind == "error",
        }
        # Dedup
        if self._current and self._current.get("text") == text:
            self._timeout_timer.start()
            return {"ok": True, "dedup": True}
        for n in self._queue:
            if n.get("text") == text:
                return {"ok": True, "dedup": True}
        self._queue.append(msg)
        if len(self._queue) > self._max_queue:
            self._queue.pop(0)
        if not self._current:
            self._next()
        self.notificationCountChanged.emit()
        return {"ok": True}

    @Slot(str, str, str, result=dict)
    def showAction(self, text: str, action: str, kind: str = "info"):
        msg = {
            "id": int(time.time() * 1000),
            "text": text, "kind": kind,
            "timestamp": time.time(),
            "action": action,
            "persistent": True,
        }
        self._queue.insert(0, msg)
        if not self._current:
            self._next()
        return {"ok": True}

    @Slot()
    def dismiss(self):
        self._current = None
        self._timeout_timer.stop()
        self.notificationChanged.emit()
        self._next()

    @Slot()
    def clear(self):
        self._queue.clear()
        self._current = None
        self._timeout_timer.stop()
        self.notificationChanged.emit()
        self.notificationCountChanged.emit()

    def _next(self):
        if self._queue:
            self._current = self._queue.pop(0)
            if not self._current.get("persistent"):
                self._timeout_timer.start()
            self.notificationChanged.emit()
            self.notificationCountChanged.emit()
        else:
            self._current = None
            self.notificationChanged.emit()
            self.notificationCountChanged.emit()
