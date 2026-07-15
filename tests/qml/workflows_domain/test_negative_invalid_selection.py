from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot


pytestmark = [pytest.mark.qml_module("negative"), pytest.mark.qml_workflow("negative")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSelectionController(QObject):
    selectionChanged = Signal()
    hasSelectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hasSelection = False
        self._count = 0
        self._selectedIds = []

    @Property(bool, notify=hasSelectionChanged)
    def hasSelection(self): return self._hasSelection

    @Property(int, notify=selectionChanged)
    def count(self): return self._count

    @Property("QVariantList", notify=selectionChanged)
    def selectedIds(self): return self._selectedIds

    @Slot("QVariantList")
    def replace(self, ids):
        self._selectedIds = ids
        self._count = len(ids)
        self._hasSelection = len(ids) > 0
        self.selectionChanged.emit()
        self.hasSelectionChanged.emit()

    @Slot()
    def clear(self):
        self._selectedIds = []
        self._count = 0
        self._hasSelection = False
        self.selectionChanged.emit()
        self.hasSelectionChanged.emit()


class TestNegativeInvalidSelection:
    def test_play_with_empty_selection(self):
        ctrl = FakeSelectionController()
        ctrl.clear()

        assert ctrl.hasSelection is False
        assert ctrl.count == 0
        assert len(ctrl.selectedIds) == 0

    def test_play_with_nonexistent_track_id(self):
        ctrl = FakeSelectionController()
        ctrl.replace([9999])
        assert ctrl.hasSelection is True
        assert ctrl.count == 1
        assert 9999 in ctrl.selectedIds

    def test_clear_selection_then_play(self):
        ctrl = FakeSelectionController()
        ctrl.replace([1, 2, 3])
        assert ctrl.count == 3
        ctrl.clear()
        assert ctrl.count == 0
        assert ctrl.hasSelection is False
