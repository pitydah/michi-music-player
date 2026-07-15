from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import logging
import time

from core.notification_service import Notification, NotificationService, NotificationType

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

    def __init__(self, action_registry=None, job_bridge=None,
                 notification_service=None, navigation_bridge=None,
                 diagnostics_service=None, parent=None):
        super().__init__(parent)
        self._action_registry = action_registry
        self._job_bridge = job_bridge
        self._notification_service: NotificationService | None = notification_service
        self._navigation_bridge = navigation_bridge
        self._diagnostics_service = diagnostics_service
        self._current: dict | None = None
        self._queue: list[dict] = []
        self._max_queue = 20
        self._priority_map: dict[str, int] = {}
        self._dedup_map: dict[str, str] = {}
        self._persistent_map: dict[str, dict] = {}
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(_DEFAULT_TIMEOUT_MS)
        self._timeout_timer.timeout.connect(self._next)

        if self._notification_service is not None:
            self._notification_service.on(self._on_service_notification)

    def _on_service_notification(self, n: Notification):
        kind = n.type.value if isinstance(n.type, NotificationType) else "info"
        text = n.message or n.title
        if n.type == NotificationType.PROGRESS:
            self.showProgress(text, n.job_id or n.id, int(n.progress) if n.progress >= 0 else 0, kind=kind)
        elif n.actions:
            action = n.actions[0] if n.actions else ""
            self.showAction(text, action, kind=kind)
        else:
            self.showMessage(text, kind=kind, persistent=n.persistent)

    @Property("QVariant", notify=notificationChanged)
    def currentNotification(self):
        return dict(self._current) if self._current else None

    @Property(int, notify=notificationCountChanged)
    def queueLength(self):
        return len(self._queue)

    @Property("QVariantList", notify=notificationChanged)
    def persistentNotifications(self):
        return list(self._persistent_map.values())

    @Slot(str, str, result=dict)
    def showMessage(self, text: str, kind: str = "info", persistent: bool | None = None):
        if persistent is None:
            persistent = kind == "error"
        msg = self._build_notification(text, kind=kind, persistent=persistent)
        dedup_key = msg.get("_dedup_key", text)
        if self._dedup(dedup_key, msg):
            return {"ok": True, "dedup": True}
        self._queue.append(msg)
        if len(self._queue) > self._max_queue:
            self._queue.pop(0)
        if not self._current:
            self._next()
        self.notificationCountChanged.emit()
        if msg.get("persistent"):
            self._persistent_map[msg["id"]] = msg
            self.notificationChanged.emit()
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
        self._persistent_map[msg["id"]] = msg
        self.notificationChanged.emit()
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

    @Slot(str, result=dict)
    def dismiss(self, notification_id: str = ""):
        if notification_id:
            self._persistent_map.pop(notification_id, None)
            if self._notification_service:
                self._notification_service.dismiss(notification_id)
        if not notification_id or (self._current and str(self._current.get("id", "")) == notification_id):
            if self._current:
                self._persistent_map.pop(self._current.get("id"), None)
            self._current = None
            self._timeout_timer.stop()
            self.notificationChanged.emit()
            self._next()
        return {"ok": True}

    @Slot()
    def clear(self):
        self._queue.clear()
        self._current = None
        self._timeout_timer.stop()
        self._dedup_map.clear()
        self._priority_map.clear()
        self._persistent_map.clear()
        if self._notification_service:
            self._notification_service.clear()
        self.notificationChanged.emit()
        self.notificationCountChanged.emit()

    @Slot(result=dict)
    def executeCurrentAction(self):
        if not self._current:
            return {"ok": False, "error": "NO_CURRENT_NOTIFICATION"}
        action_id = self._current.get("action", "")
        if not action_id:
            return {"ok": False, "error": "NO_ACTION"}
        result = self._execute_action(action_id, self._current)
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
            target = self._persistent_map.get(notification_id)
        if not target:
            return {"ok": False, "error": "NOT_FOUND"}
        action_id = target.get("action", "")
        if not action_id:
            return {"ok": False, "error": "NO_ACTION"}
        self._current = target
        if target in self._queue:
            self._queue.remove(target)
        self.notificationChanged.emit()
        result = self._execute_action(action_id, target)
        self.actionExecuted.emit(action_id, result)
        return result

    def _execute_action(self, action_id: str, notification: dict | None = None) -> dict:
        if not action_id:
            return {"ok": False, "error": "NO_ACTION"}
        if action_id == "openJob" and notification:
            return self.openJob(notification.get("job_id", ""))
        if action_id == "cancelJob" and notification:
            return self.cancelJobById(notification.get("job_id", ""))
        if action_id == "retry" and notification:
            return self.retry(notification.get("id", ""))
        if action_id == "undo":
            result = self.undoAction(notification.get("undo_key", "") if notification else "")
            return result
        if action_id == "openTrack" and notification:
            track_id = notification.get("entity", "").replace("track_", "")
            if track_id.isdigit():
                return self.showTrack(int(track_id))
            return {"ok": False, "error": "INVALID_TRACK"}
        if action_id == "openAlbum" and notification:
            return self.showTrack(0, album_key=notification.get("entity", ""))
        if action_id == "openDevice" and notification:
            return self.showDevice(notification.get("entity", ""))
        if action_id == "openDiagnostics":
            return self.openDiagnostics()
        if action_id == "openSettings":
            return self.openSettings()
        if self._action_registry:
            try:
                result = self._action_registry.execute(action_id)
                return result if isinstance(result, dict) else {"ok": True, "result": str(result)}
            except Exception as e:
                logger.debug("Action execution failed: %s", e)
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_ACTION_REGISTRY"}

    @Slot(str, result=dict)
    def openJob(self, job_id: str):
        if self._job_bridge and hasattr(self._job_bridge, 'navigateToJob'):
            try:
                return self._job_bridge.navigateToJob(job_id)
            except Exception:
                pass
        if self._navigation_bridge:
            self._navigation_bridge.navigate("audio_lab.jobs")
            return {"ok": True}
        if self._action_registry:
            return self._action_registry.execute("navigate_jobs")
        return {"ok": False, "error": "NO_NAVIGATION_TARGET"}

    @Slot(str, result=dict)
    def cancelJobById(self, job_id: str):
        if self._job_bridge and hasattr(self._job_bridge, 'cancelJob'):
            try:
                job_id_int = int(job_id) if job_id.isdigit() else None
                if job_id_int is not None:
                    return self._job_bridge.cancelJob(job_id_int)
            except Exception:
                pass
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(str, result=dict)
    def retry(self, notification_id: str):
        try:
            return self.executeNotificationAction(notification_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def retryJob(self, job_id: str):
        if self._job_bridge and hasattr(self._job_bridge, 'retryJob'):
            try:
                return self._job_bridge.retryJob(job_id)
            except Exception:
                pass
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(str, result=dict)
    def undoAction(self, undo_key: str):
        if self._action_registry:
            try:
                result = self._action_registry.execute(f"undo_{undo_key}")
                return result if isinstance(result, dict) else {"ok": True}
            except Exception:
                pass
        return {"ok": False, "error": "UNSUPPORTED_UNDO"}

    @Slot(int, result=dict)
    def showTrack(self, track_id: int, album_key: str = ""):
        if album_key and self._navigation_bridge:
            self._navigation_bridge.navigateWithParams("library.album_detail", {"album_key": album_key})
            return {"ok": True}
        if self._action_registry:
            return self._action_registry.execute("track_open_album")
        return {"ok": False, "error": "NO_ACTION"}

    @Slot(str, result=dict)
    def showDevice(self, device_id: str):
        if self._navigation_bridge:
            self._navigation_bridge.navigate("home_audio")
            return {"ok": True}
        if self._action_registry:
            return self._action_registry.execute("navigate_home_audio")
        return {"ok": False, "error": "NO_NAVIGATION"}

    @Slot(result=dict)
    def openDiagnostics(self):
        if self._navigation_bridge:
            self._navigation_bridge.navigate("diagnostics")
            return {"ok": True}
        if self._action_registry:
            return self._action_registry.execute("navigate_diagnostics")
        return {"ok": False, "error": "NO_NAVIGATION"}

    @Slot(result=dict)
    def openSettings(self):
        if self._navigation_bridge:
            self._navigation_bridge.navigate("settings.general")
            return {"ok": True}
        if self._action_registry:
            return self._action_registry.execute("navigate_settings")
        return {"ok": False, "error": "NO_NAVIGATION"}

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

    @Slot(str, result=dict)
    def showBanner(self, text: str, kind: str = "info"):
        msg = self._build_notification(text, kind=kind, persistent=True)
        msg["_priority"] = _PRIORITY_HIGH
        msg["banner"] = True
        self._queue.insert(0, msg)
        if not self._current:
            self._next()
        self._persistent_map[msg["id"]] = msg
        self.notificationChanged.emit()
        return {"ok": True, "banner": True}

    @Slot(str, str, result=dict)
    def showCenter(self, text: str, kind: str = "info"):
        msg = self._build_notification(text, kind=kind, persistent=True)
        msg["_priority"] = _PRIORITY_HIGH
        msg["center"] = True
        self._queue.insert(0, msg)
        if not self._current:
            self._next()
        self._persistent_map[msg["id"]] = msg
        self.notificationChanged.emit()
        return {"ok": True, "center": True}

    @Slot(str, str, result=dict)
    def showPersistentError(self, text: str, error_code: str = ""):
        return self.showMessage(text, kind="error", persistent=True)

    @Slot(str, str, result=dict)
    def showProgressNotification(self, text: str, job_id: str):
        return self.showProgress(text, job_id, 0)

    @Slot(str, str, result=dict)
    def cancelAndNotify(self, job_id: str, reason: str = ""):
        result = self.cancelJobById(job_id)
        text = reason or f"Tarea {job_id} cancelada."
        self.showMessage(text, kind="info")
        return result

    @Slot(str, str, result=dict)
    def retryAndNotify(self, job_id: str, reason: str = ""):
        result = self.retryJob(job_id)
        if result.get("ok"):
            text = reason or f"Reintentando tarea {job_id}..."
            self.showMessage(text, kind="info")
        return result

    @Slot(str, str, result=dict)
    def undoAndNotify(self, undo_key: str, action_name: str = ""):
        result = self.undoAction(undo_key)
        if result.get("ok"):
            text = f"Accion '{action_name or undo_key}' deshecha."
            self.showMessage(text, kind="success")
        return result

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
            "id": str(int(time.time() * 1000)),
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

    @Slot(result=dict)
    def notificationScore(self) -> dict:
        score = 0
        if self._current is not None:
            score += 10
        if len(self._queue) > 0:
            score += 5
        if self._action_registry:
            score += 15
        if self._job_bridge:
            score += 10
        if self._notification_service:
            score += 15
        if self._navigation_bridge:
            score += 15
        if self._diagnostics_service:
            score += 10
        if hasattr(self, 'openJob') and callable(self.openJob):
            score += 5
        if hasattr(self, 'retryJob') and callable(self.retryJob):
            score += 5
        if hasattr(self, 'showTrack') and callable(self.showTrack):
            score += 5
        if hasattr(self, 'showDevice') and callable(self.showDevice):
            score += 5
        if hasattr(self, 'openDiagnostics') and callable(self.openDiagnostics):
            score += 5
        if hasattr(self, 'openSettings') and callable(self.openSettings):
            score += 5
        return {
            "score": min(100, score),
            "has_current": self._current is not None,
            "queue_length": len(self._queue),
            "has_action_registry": self._action_registry is not None,
            "has_job_bridge": self._job_bridge is not None,
            "has_notification_service": self._notification_service is not None,
            "has_navigation_bridge": self._navigation_bridge is not None,
            "has_diagnostics_service": self._diagnostics_service is not None,
            "timeout_active": self._timeout_timer.isActive(),
        }
