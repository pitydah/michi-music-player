"""QueueBridge — provides QueueListModel and queue actions to QML."""
from __future__ import annotations

import json
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

    def __init__(self, player_service=None, playlists_bridge=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._pb = playlists_bridge
        from ui_qml.models.QueueListModel import QueueListModel
        self._model = QueueListModel(player_service=player_service, parent=self)
        from core.queue_service import QueueService
        self._queue_service = QueueService(player_service=player_service)

    @property
    def queue_service(self):
        return self._queue_service

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
            shuffle = self._player.get_shuffle() if hasattr(self._player, 'get_shuffle') else False
            repeat = self._player.get_repeat() if hasattr(self._player, 'get_repeat') else "none"
            items = []
            for i in (q or []):
                if isinstance(i, dict):
                    items.append({
                        "id": i.get("id", i.get("track_id", "")),
                        "track_uid": i.get("track_uid", ""),
                        "title": i.get("title", ""),
                        "artist": i.get("artist", ""),
                        "album": i.get("album", ""),
                        "duration": i.get("duration", 0),
                        "source": i.get("source_type", "local_file"),
                    })
            import time
            state = {
                "version": 1,
                "timestamp": time.time(),
                "current_index": 0,
                "position": 0,
                "shuffle": shuffle,
                "repeat": repeat,
                "source": "queue_bridge",
                "items": items,
            }
            path = _queue_state_path()
            with open(path, "w") as f:
                json.dump(state, f)
            return {"ok": True, "path": path, "count": len(items)}
        except Exception as e:
            logger.exception("saveState failed")
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def loadState(self):
        path = _queue_state_path()
        if not os.path.exists(path):
            return {"ok": False, "error": "NO_SAVED_STATE"}
        try:
            with open(path) as f:
                state = json.load(f)
            items = state.get("items", [])
            if not items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if not self._player or not hasattr(self._player, 'set_queue'):
                return {"ok": False, "error": "UNSUPPORTED"}
            resolved = []
            for item in items:
                track = self._resolve_track(item)
                if track:
                    resolved.append(track)
            self._player.set_queue(resolved)
            self.refresh()
            return {"ok": True, "count": len(resolved)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _resolve_track(self, item: dict) -> dict | None:
        """Resolve a saved item to a current track by ID."""
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
