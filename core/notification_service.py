from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"


@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    progress: float = -1.0
    persistent: bool = False
    dismissible: bool = True
    actions: list[str] = field(default_factory=list)
    source: str = ""
    entity: str = ""
    job_id: str = ""
    error_code: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp,
            "progress": self.progress,
            "persistent": self.persistent,
            "dismissible": self.dismissible,
            "actions": list(self.actions),
            "source": self.source,
            "entity": self.entity,
            "job_id": self.job_id,
            "error_code": self.error_code,
        }


class NotificationService:
    def __init__(self):
        self._lock = threading.Lock()
        self._notifications: dict[str, Notification] = {}
        self._listeners: list[Callable] = []
        self._max_size = 200
        self._persistent_ids: set[str] = set()

    def notify(self, notification: Notification) -> Notification:
        with self._lock:
            self._notifications[notification.id] = notification
            if notification.persistent:
                self._persistent_ids.add(notification.id)
            self._trim()
        self._emit(notification)
        return notification

    def update(self, notification_id: str, **kwargs) -> Notification | None:
        with self._lock:
            n = self._notifications.get(notification_id)
            if not n:
                return None
            for k, v in kwargs.items():
                if hasattr(n, k):
                    setattr(n, k, v)
            n.timestamp = time.time()
        self._emit(n)
        return n

    def dismiss(self, notification_id: str) -> bool:
        with self._lock:
            n = self._notifications.get(notification_id)
            if not n or not n.dismissible:
                return False
            self._notifications.pop(notification_id, None)
            self._persistent_ids.discard(notification_id)
        return True

    def get(self, notification_id: str) -> Notification | None:
        with self._lock:
            return self._notifications.get(notification_id)

    def list_all(self) -> list[Notification]:
        with self._lock:
            return list(self._notifications.values())

    def list_persistent(self) -> list[Notification]:
        with self._lock:
            return [self._notifications[nid] for nid in self._persistent_ids if nid in self._notifications]

    def list_by_source(self, source: str) -> list[Notification]:
        with self._lock:
            return [n for n in self._notifications.values() if n.source == source]

    def clear(self):
        with self._lock:
            self._notifications.clear()
            self._persistent_ids.clear()

    def on(self, listener: Callable):
        self._listeners.append(listener)

    def off(self, listener: Callable):
        self._listeners.remove(listener)

    def _trim(self):
        if len(self._notifications) <= self._max_size:
            return
        non_persistent = {nid: n for nid, n in self._notifications.items() if not n.persistent}
        sorted_np = sorted(non_persistent.items(), key=lambda x: x[1].timestamp)
        to_remove = sorted_np[:len(self._notifications) - self._max_size]
        for nid, _ in to_remove:
            self._notifications.pop(nid, None)
            self._persistent_ids.discard(nid)

    def _emit(self, notification: Notification):
        for listener in self._listeners:
            try:
                listener(notification)
            except Exception:
                continue
