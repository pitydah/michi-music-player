"""SelectionContextBridge — shared selection state for tracks/albums/playlists.

Delegates to SelectionController for storage and operations to avoid duplicate implementations.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from .selection_controller import SelectionController


class SelectionContextBridge(QObject):
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctrl = SelectionController(parent)
        self._selected_data: dict = {}
        self._primary_id = ""

        self._ctrl.selectionChanged.connect(self._on_ctrl_changed)

    def _on_ctrl_changed(self):
        self.selectionChanged.emit()

    @Property(bool, notify=selectionChanged)
    def hasSelection(self):
        return self._ctrl.hasSelection

    @Property(int, notify=selectionChanged)
    def selectionCount(self):
        return self._ctrl.count

    @Property(str, notify=selectionChanged)
    def primaryId(self):
        return self._primary_id

    @Property("QVariant", notify=selectionChanged)
    def selectedData(self):
        return self._selected_data

    @Slot(str, result=dict)
    def setSelectedId(self, item_id: str):
        self._primary_id = item_id
        try:
            self._ctrl.replace([int(item_id)])
        except (ValueError, TypeError):
            self._ctrl.replace([])
        self._selected_data = {"id": item_id}
        self.selectionChanged.emit()
        return {"ok": True}

    @Slot("QVariant", result=dict)
    def setSelected(self, data: dict):
        self._selected_data = data
        self._primary_id = str(data.get("id", data.get("track_id", "")))
        try:
            self._ctrl.replace([int(self._primary_id)])
        except (ValueError, TypeError):
            self._ctrl.replace([])
        self.selectionChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearSelection(self):
        self._ctrl.clear()
        self._selected_data = {}
        self._primary_id = ""
        self.selectionChanged.emit()
        return {"ok": True}

    @Property(str, notify=selectionChanged)
    def selectedTrackId(self):
        return str(self._selected_data.get("id", self._selected_data.get("track_id", "")))

    @Property(str, notify=selectionChanged)
    def selectedFilepath(self):
        return ""

    @Property(str, notify=selectionChanged)
    def selectedTitle(self):
        return self._selected_data.get("title", "")
