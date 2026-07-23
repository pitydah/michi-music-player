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

    @Property(int, notify=dataChanged)
    def currentIndex(self) -> int:
        return self._queue_service.current_index

    @Slot("QVariantList", result=dict)
    def add(self, items: list) -> dict:
        """Append queue items without interrupting current playback."""
        try:
            return self._queue_service.enqueue(items, play_now=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @Slot("QVariantList", int, result=dict)
    def replaceAndPlay(self, items: list, start_index: int) -> dict:
        """Atomically replace the queue and start at a validated index."""
        if not items:
            return {"ok": False, "error": "EMPTY_QUEUE"}
        if start_index < 0 or start_index >= len(items):
            return {"ok": False, "error": "INVALID_INDEX"}
        try:
            return self._queue_service.replace_and_play(items, start_index)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

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
        playlist_name = name.strip()
        if not playlist_name:
            return {"ok": False, "error": "EMPTY_NAME"}
        if not self._pb:
            return {"ok": False, "error": "NO_PLAYLIST_BRIDGE"}
        items = self._queue_service.items
        if not items:
            return {"ok": False, "error": "EMPTY_QUEUE"}
        try:
            return self._pb.saveQueueAsPlaylist(playlist_name, items)
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
        self._model.shutdown()
