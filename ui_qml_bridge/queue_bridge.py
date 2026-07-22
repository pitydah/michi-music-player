"""QueueBridge — adapts QueueService for QML, with QueueListModel as observer."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.queue_bridge")


class QueueBridge(QObject):
    """Expose canonical queue commands and reactive state to QML."""

    dataChanged = Signal()
    _domainChanged = Signal()

    def __init__(self, player_service=None, playlists_bridge=None,
                 queue_service=None, parent=None) -> None:
        super().__init__(parent)
        assert queue_service is not None, "QueueBridge: queue_service is REQUIRED"
        self._player = player_service
        self._pb = playlists_bridge
        self._queue_service = queue_service
        from ui_qml.models.QueueListModel import QueueListModel
        self._model = QueueListModel(queue_service=queue_service, parent=self)
        self._unsubscribe = queue_service.subscribe(self._on_queue_event)
        self._domainChanged.connect(self.dataChanged.emit)
        self.destroyed.connect(self._unsubscribe_queue)

    def _on_queue_event(self, event: str, state: dict) -> None:
        if event != "operationFailed":
            self._domainChanged.emit()

    @Slot()
    def _unsubscribe_queue(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    @property
    def queue_service(self):
        return self._queue_service

    @Property(bool, notify=dataChanged)
    def canUndo(self) -> bool:
        return self._queue_service.can_undo

    @Property("QVariant", notify=dataChanged)
    def queueModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def queueCount(self) -> int:
        return self._model.totalCount if self._model else 0

    @Slot(result=dict)
    def refresh(self) -> dict:
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.queueCount}

    @Slot(int, result=dict)
    def playFromIndex(self, index: int) -> dict:
        return self._queue_service.play_from_index(index)

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int) -> dict:
        try:
            return self._queue_service.remove([index])
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def moveItem(self, from_index: int, to_index: int) -> dict:
        try:
            return self._queue_service.reorder(from_index, to_index)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def saveAsPlaylist(self, name: str) -> dict:
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        if not self._pb:
            return {"ok": False, "error": "NO_PLAYLIST_BRIDGE"}
        try:
            return self._pb.saveQueueAsPlaylist(name, self._queue_service.items)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def clearQueue(self) -> dict:
        try:
            return self._queue_service.clear()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def saveState(self) -> dict:
        if self._queue_service:
            return self._queue_service.save_state()
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def loadState(self) -> dict:
        if self._queue_service:
            return self._queue_service.load_state()
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def undo(self) -> dict:
        if self._queue_service:
            try:
                return self._queue_service.undo()
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def persist(self) -> dict:
        if self._queue_service:
            return self._queue_service.persist()
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def restore(self) -> dict:
        if self._queue_service:
            return self._queue_service.restore()
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result="QVariantList")
    def missingTracks(self) -> list[dict]:
        if self._queue_service:
            return self._queue_service.missing_tracks()
        return []

    def shutdown(self) -> None:
        self._unsubscribe_queue()

    def _resolve_track(self, item: dict) -> dict | None:
        tid = item.get("id", item.get("track_id", ""))
        if not self._player or not hasattr(self._player, 'get_track_by_id'):
            return item
        try:
            track = self._player.get_track_by_id(tid)
            if track:
                return track
        except Exception:
            pass
        return item
