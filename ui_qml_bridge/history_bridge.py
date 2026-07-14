"""HistoryBridge — paginated play history via HistoryQueryService SQL JOIN, no N+1."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml.models.HistoryListModel import HistoryListModel


class HistoryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, history_query_service=None, query_executor=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._hqs = history_query_service
        self._qe = query_executor
        self._model = HistoryListModel(db=db, history_query_service=history_query_service,
                                       query_executor=query_executor, parent=self)

    @Property("QVariant", notify=dataChanged)
    def historyModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def historyCount(self):
        return self._model.totalCount

    @Property("QVariant", notify=dataChanged)
    def historyQueryService(self):
        return self._hqs

    @Property("QVariant", notify=dataChanged)
    def playbackBridge(self):
        return getattr(self, '_playback_bridge', None)

    def setPlaybackBridge(self, bridge):
        self._playback_bridge = bridge

    @Slot(result=dict)
    def refresh(self):
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.historyCount}

    @Slot(str, result=dict)
    def removeHistoryItem(self, track_id: str):
        if self._hqs:
            result = self._hqs.remove_history_item(track_id)
            self.refresh()
            return result
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history WHERE track_id=?", (track_id,))
            self._db.conn.commit()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def clearHistory(self):
        if self._hqs:
            result = self._hqs.clear_history()
            self.refresh()
            return result
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history")
            self._db.conn.commit()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(bool, result=dict)
    def setHistoryEnabled(self, enabled: bool):
        if self._hqs:
            return self._hqs.set_history_enabled(enabled)
        return {"ok": True}

    @Slot(int, result=dict)
    def setHistoryLimit(self, limit: int):
        if self._hqs:
            return self._hqs.set_history_limit(limit)
        return {"ok": True}
