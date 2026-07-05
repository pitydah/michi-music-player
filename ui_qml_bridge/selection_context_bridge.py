"""SelectionContextBridge — shared selection state for tracks/albums/playlists."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class SelectionContextBridge(QObject):
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_ids: list[str] = []
        self._selected_data: dict = {}
        self._selection_count = 0
        self._primary_id = ""

    @Property(bool, notify=selectionChanged)
    def hasSelection(self):
        return self._selection_count > 0

    @Property(int, notify=selectionChanged)
    def selectionCount(self):
        return self._selection_count

    @Property(str, notify=selectionChanged)
    def primaryId(self):
        return self._primary_id

    @Property("QVariant", notify=selectionChanged)
    def selectedData(self):
        return self._selected_data

    @Slot(str, result=dict)
    def setSelectedId(self, item_id: str):
        self._selected_ids = [item_id]
        self._primary_id = item_id
        self._selection_count = 1
        self.selectionChanged.emit()
        return {"ok": True}

    @Slot("QVariant", result=dict)
    def setSelected(self, data: dict):
        self._selected_data = data
        self._primary_id = str(data.get("id", data.get("track_id", "")))
        self._selection_count = 1
        self.selectionChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearSelection(self):
        self._selected_ids = []
        self._selected_data = {}
        self._selection_count = 0
        self._primary_id = ""
        self.selectionChanged.emit()
        return {"ok": True}

    @Property(str, notify=selectionChanged)
    def selectedTrackId(self):
        return str(self._selected_data.get("id", self._selected_data.get("track_id", "")))

    @Property(str, notify=selectionChanged)
    def selectedFilepath(self):
        return self._selected_data.get("filepath", "")

    @Property(str, notify=selectionChanged)
    def selectedTitle(self):
        return self._selected_data.get("title", "")
