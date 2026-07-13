"""QueueBridge — provides QueueListModel and queue actions to QML."""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.queue_bridge")


class QueueBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, playlists_bridge=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._pb = playlists_bridge
        from ui_qml.models.QueueListModel import QueueListModel
        self._model = QueueListModel(player_service=player_service, parent=self)

    @Property("QVariant", notify=dataChanged)
    def queueModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def queueCount(self):
        return self._model.totalCount

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
        if not self._player or not hasattr(self._player, 'remove_from_queue'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.remove_from_queue(index)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def moveItem(self, from_index: int, to_index: int):
        if not self._player or not hasattr(self._player, 'move_in_queue'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.move_in_queue(from_index, to_index)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
        if not self._player or not hasattr(self._player, 'clear_queue'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.clear_queue()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def saveState(self):
        if not self._player or not hasattr(self._player, 'get_queue'):
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            q = self._player.get_queue()
            state = {
                "items": [
                    {"id": i.get("id", i.get("track_id", "")),
                     "title": i.get("title", ""),
                     "artist": i.get("artist", ""),
                     "album": i.get("album", ""),
                     "duration": i.get("duration", 0)}
                    for i in (q or [])
                    if isinstance(i, dict)
                ],
            }
            import tempfile
            import os
            path = os.path.join(tempfile.gettempdir(), "michi_queue_state.json")
            with open(path, "w") as f:
                json.dump(state, f)
            return {"ok": True, "path": path, "count": len(state["items"])}
        except Exception as e:
            logger.exception("saveState failed")
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def loadState(self):
        import os
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "michi_queue_state.json")
        if not os.path.exists(path):
            return {"ok": False, "error": "NO_SAVED_STATE"}
        try:
            with open(path) as f:
                state = json.load(f)
            items = state.get("items", [])
            if not self._player or not hasattr(self._player, 'set_queue'):
                return {"ok": False, "error": "UNSUPPORTED"}
            self._player.set_queue(items)
            self.refresh()
            return {"ok": True, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
