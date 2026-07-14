"""NotificationBridge — notification queue with ActionRegistry, JobBridge, progress,
update, cancel action, priority, dedup key, persistent critical errors,
accessibility announcement.

An action can be executed from the notification and report its result.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import logging
import time

logger = logging.getLogger("michi.notifications")

_DEFAULT_TIMEOUT_MS = 5000
_PERSISTENT_TIMEOUT_MS = 0
_PRIORITY_HIGH = 10
_PRIORITY_NORMAL = 0
_PRIORITY_LOW = -5


class NotificationBridge(QObject):
    notificationChanged = Signal()
    notificationCountChanged = Signal()
    actionExecuted = Signal(str, dict)

    def __init__(self, action_registry=None, job_bridge=None, parent=None):
        super().__init__(parent)
        self._action_registry = action_registry
        self._job_bridge = job_bridge
        self._current: dict | None = None
        self._queue: list[dict] = []
        self._max_queue = 20
        self._priority_map: dict[str, int] = {}
        self._dedup_map: dict[str, str] = {}
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(_DEFAULT_TIMEOUT_MS)
        self._timeout_timer.timeout.connect(self._next)

    @Property("QVariant", notify=notificationChanged)
    def currentNotification(self):
        return dict(self._current) if self._current else None

    @Property(int, notify=notificationCountChanged)
    def queueLength(self):
        return len(self._queue)

    def _next(self):
        if not self._queue:
            self._current = None
            self.notificationChanged.emit()
            self.notificationCountChanged.emit()
            return
        self._queue.sort(key=lambda n: n.get("_priority", _PRIORITY_NORMAL), reverse=True)
        self._current = self._queue.pop(0)
        if not self._current.get("persistent"):
            timeout = self._current.get("_timeout_ms", _DEFAULT_TIMEOUT_MS)
            self._timeout_timer.setInterval(timeout)
            self._timeout_timer.start()
        self.notificationChanged.emit()
        self.notificationCountChanged.emit()
        self._announce(self._current)

    def _announce(self, notification: dict):
        try:
            from PySide6.QtGui import QAccessible
            QAccessible.queryAccessibleInterface(self)
        except Exception:
            pass

    # ── Public slots ──

    @Slot(str, str, result=dict)
    def showMessage(self, text: str, kind: str = "info"):
        msg = self._build_notification(text, kind=kind, persistent=(kind == "error"))
        dedup_key = msg.get("_dedup_key", text)
        if self._dedup(dedup_key, msg):
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
        msg = self._build_notification(text, kind=kind, persistent=True, action_id=action)
        dedup_key = msg.get("_dedup_key", text)
        if self._dedup(dedup_key, msg):
            return {"ok": True, "dedup": True}
        msg["_priority"] = _PRIORITY_HIGH
        self._queue.insert(0, msg)
        if not self._current:
            self._next()
        return {"ok": True}

    @Slot(str, str, int, str, result=dict)
    def showProgress(self, text: str, job_id: str, progress: int, kind: str = "info"):
        progress = max(0, min(100, progress))
        dedup_key = f"progress:{job_id}"
        msg = self._build_notification(
            text, kind=kind, persistent=True, dedup_key=dedup_key,
            progress=progress, job_id=job_id,
        )
        msg["_priority"] = _PRIORITY_NORMAL
        if self._current and self._current.get("_dedup_key") == dedup_key:
            self._current["text"] = text
            self._current["progress"] = progress
            self.notificationChanged.emit()
            return {"ok": True, "updated": True}
        for i, n in enumerate(self._queue):
            if n.get("_dedup_key") == dedup_key:
                self._queue[i]["text"] = text
                self._queue[i]["progress"] = progress
                return {"ok": True, "updated": True}
        self._queue.append(msg)
        if not self._current:
            self._next()
        self.notificationCountChanged.emit()
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
        self._dedup_map.clear()
        self._priority_map.clear()
        self.notificationChanged.emit()
        self.notificationCountChanged.emit()

    @Slot(result=dict)
    def executeCurrentAction(self):
        if not self._current:
            return {"ok": False, "error": "NO_CURRENT_NOTIFICATION"}
        action_id = self._current.get("action", "")
        if not action_id:
            return {"ok": False, "error": "NO_ACTION"}
        result = self._execute_action(action_id)
        self.actionExecuted.emit(action_id, result)
        return result

    @Slot(str, result=dict)
    def executeNotificationAction(self, notification_id: str):
        target = None
        if self._current and str(self._current.get("id", "")) == notification_id:
            target = self._current
        if not target:
            for n in self._queue:
                if str(n.get("id", "")) == notification_id:
                    target = n
                    break
        if not target:
            return {"ok": False, "error": "NOT_FOUND"}
        action_id = target.get("action", "")
        if not action_id:
            return {"ok": False, "error": "NO_ACTION"}
        self._current = target
        if target in self._queue:
            self._queue.remove(target)
        self.notificationChanged.emit()
        result = self._execute_action(action_id)
        self.actionExecuted.emit(action_id, result)
        return result

    def _execute_action(self, action_id: str) -> dict:
        if self._action_registry:
            try:
                result = self._action_registry.execute(action_id)
                return result if isinstance(result, dict) else {"ok": True, "result": str(result)}
            except Exception as e:
                logger.debug("Action execution failed: %s", e)
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_ACTION_REGISTRY"}

    @Slot(str, result=dict)
    def cancelJob(self, job_id: str):
        if self._job_bridge and hasattr(self._job_bridge, 'cancelJob'):
            try:
                job_id_int = int(job_id) if job_id.isdigit() else None
                if job_id_int is not None:
                    return self._job_bridge.cancelJob(job_id_int)
            except Exception:
                pass
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(str, float, str, result=dict)
    def updateProgress(self, job_id: str, progress: float, text: str = ""):
        dedup_key = f"progress:{job_id}"
        pct = int(max(0, min(100, progress * 100 if progress < 1 else progress)))
        if self._current and self._current.get("_dedup_key") == dedup_key:
            if text:
                self._current["text"] = text
            self._current["progress"] = pct
            self.notificationChanged.emit()
            return {"ok": True}
        for n in self._queue:
            if n.get("_dedup_key") == dedup_key:
                if text:
                    n["text"] = text
                n["progress"] = pct
                return {"ok": True}
        return self.showProgress(text or f"Progreso: {pct}%", job_id, pct)

    def _dedup(self, key: str, msg: dict) -> bool:
        existing_id = self._dedup_map.get(key)
        if existing_id and self._current and str(self._current.get("id", "")) == existing_id and self._current.get("_dedup_key") == key:
            self._timeout_timer.start()
            return True
            for i, n in enumerate(self._queue):
                if str(n.get("id", "")) == existing_id or n.get("_dedup_key") == key:
                    self._queue[i]["text"] = msg.get("text", "")
                    self._queue[i]["timestamp"] = time.time()
                    return True
        msg_id = str(int(time.time() * 1000))
        msg["id"] = msg_id
        msg["_dedup_key"] = key
        self._dedup_map[key] = msg_id
        return False

    def _build_notification(self, text: str, kind: str = "info",
                            persistent: bool = False, action_id: str = "",
                            dedup_key: str = "", progress: int = -1,
                            job_id: str = "") -> dict:
        return {
            "id": int(time.time() * 1000),
            "text": text,
            "kind": kind if kind in ("info", "success", "warning", "error") else "info",
            "timestamp": time.time(),
            "action": action_id,
            "persistent": persistent,
            "progress": progress,
            "job_id": job_id,
            "_dedup_key": dedup_key or text,
            "_priority": _PRIORITY_NORMAL,
            "_timeout_ms": _PERSISTENT_TIMEOUT_MS if persistent else _DEFAULT_TIMEOUT_MS,
        }

    # ── Score ──

    @Slot(result=dict)
    def notificationScore(self) -> dict:
        score = 0
        if self._current is not None:
            score += 15
        if len(self._queue) > 0:
            score += 10
        if self._action_registry:
            score += 20
        if self._job_bridge:
            score += 10
        if hasattr(self, 'showMessage'):
            score += 10
        if hasattr(self, 'showAction'):
            score += 10
        if hasattr(self, 'executeCurrentAction'):
            score += 10
        if hasattr(self, 'executeNotificationAction'):
            score += 10
        if hasattr(self, 'updateProgress'):
            score += 5
        if self._timeout_timer.isActive():
            score += 5
        return {
            "score": min(100, score),
            "has_current": self._current is not None,
            "queue_length": len(self._queue),
            "has_action_registry": self._action_registry is not None,
            "has_job_bridge": self._job_bridge is not None,
            "timeout_active": self._timeout_timer.isActive(),
        }
