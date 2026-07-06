"""QueueBridge — provides QueueListModel and queue actions to QML."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class QueueBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self._player = player_service
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
