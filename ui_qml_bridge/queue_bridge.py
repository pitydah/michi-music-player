"""QueueBridge — adapts QueueService for QML, with QueueListModel as observer."""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Signal, Property, Slot


def _queue_state_path():
    try:
        from core.paths import app_config_dir
        p = app_config_dir()
        if p:
            return str(p / "queue_state.json")
    except Exception:
        pass
    import tempfile
    return os.path.join(tempfile.gettempdir(), "michi_queue_state.json")

logger = logging.getLogger("michi.queue_bridge")


class QueueBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, playlists_bridge=None,
                 queue_service=None, parent=None):
        super().__init__(parent)
        assert player_service is not None, "QueueBridge: player_service is REQUIRED"
        self._player = player_service
        self._pb = playlists_bridge
        self._queue_service = queue_service
        from ui_qml.models.QueueListModel import QueueListModel
        self._model = QueueListModel(player_service=player_service, parent=self)

    @property
    def queue_service(self):
        return self._queue_service

    @Property("QVariant", notify=dataChanged)
    def queueModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def queueCount(self):
        return self._model.totalCount if self._model else 0

    @Slot(result=dict)
    def refresh(self):
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.queueCount}

    @Slot(int, result=dict)
    def playFromIndex(self, index: int):
        if not self._player or not hasattr(self._player, 'get_queue'):
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            q = self._player.get_queue()
            if not q or index < 0 or index >= len(q):
                return {"ok": False, "error": "INVALID_INDEX"}
            if hasattr(self._player, 'play_index'):
                self._player.play_index(index)
            elif hasattr(self._player, 'seek_to_index'):
                self._player.seek_to_index(index)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def removeFromQueue(self, index: int):
        if self._queue_service:
            try:
                self._queue_service.remove([index])
                self._model.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(int, int, result=dict)
    def moveItem(self, from_index: int, to_index: int):
        if self._queue_service:
            try:
                self._queue_service.reorder(from_index, to_index)
                self._model.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(str, result=dict)
    def saveAsPlaylist(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        if not self._pb:
            return {"ok": False, "error": "NO_PLAYLIST_BRIDGE"}
        if not self._player or not hasattr(self._player, 'get_queue'):
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            return self._pb.saveQueueAsPlaylist(name)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def clearQueue(self):
        if self._queue_service:
            try:
                self._queue_service.clear()
                self._model.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def saveState(self):
        if self._queue_service:
            result = self._queue_service.save_state()
            self.dataChanged.emit()
            return result
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def loadState(self):
        if self._queue_service:
            result = self._queue_service.load_state()
            self._model.refresh()
            return result
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def undo(self):
        if self._queue_service:
            try:
                self._queue_service.undo()
                self._model.refresh()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def persist(self):
        if self._queue_service:
            return self._queue_service.persist()
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result=dict)
    def restore(self):
        if self._queue_service:
            result = self._queue_service.restore()
            self._model.refresh()
            return result
        return {"ok": False, "error": "NO_QUEUE_SERVICE"}

    @Slot(result="QVariantList")
    def missingTracks(self):
        if self._queue_service:
            return self._queue_service.missing_tracks()
        return []

    def shutdown(self):
        if self._queue_service:
            self._queue_service.shutdown()

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
