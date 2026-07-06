"""HistoryBridge — provides HistoryListModel to QML."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class HistoryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        from ui_qml.models.HistoryListModel import HistoryListModel
        self._model = HistoryListModel(db=db, parent=self)

    @Property("QVariant", notify=dataChanged)
    def historyModel(self):
        return self._model

    @Property(int, notify=dataChanged)
    def historyCount(self):
        return self._model.totalCount

    @Slot(result=dict)
    def refresh(self):
        self._model.refresh()
        self.dataChanged.emit()
        return {"ok": True, "count": self.historyCount}

    @Slot(result=dict)
    def clearHistory(self):
        if not self._db or not hasattr(self._db, 'conn'):
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history")
            self._db.conn.commit()
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
