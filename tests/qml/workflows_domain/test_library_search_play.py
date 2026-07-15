from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("library"), pytest.mark.qml_workflow("search_play")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeLibraryBridge(QObject):
    stateChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "READY"
        self._songCount = 100
        self._albumCount = 10
        self._artistCount = 5
        self._searchQuery = ""
        self._playback_ctrl = MagicMock()
        self._playback_ctrl.enqueue = MagicMock()
        self._playback_ctrl.play = MagicMock()

    @Property(str, notify=stateChanged)
    def state(self): return self._state

    @Property(int, notify=dataChanged)
    def songCount(self): return self._songCount

    @Property(int, notify=dataChanged)
    def albumCount(self): return self._albumCount

    @Property(int, notify=dataChanged)
    def artistCount(self): return self._artistCount

    @Slot(str)
    def search(self, text): self._searchQuery = text

    @Slot(int, result=dict)
    def playTrackById(self, tid):
        self._playback_ctrl.play(tid)
        return {"ok": True}

    @Slot(int, result=dict)
    def enqueueTrackById(self, tid):
        self._playback_ctrl.enqueue(tid)
        return {"ok": True}

    @Slot()
    def clearFilters(self): self._searchQuery = ""

    @Slot()
    def refresh(self): self.dataChanged.emit()


class FakeSelectionController(QObject):
    selectionChanged = Signal()
    hasSelectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hasSelection = False
        self._count = 0

    @Property(bool, notify=hasSelectionChanged)
    def hasSelection(self): return self._hasSelection

    @Property(int, notify=selectionChanged)
    def count(self): return self._count

    @Slot()
    def clear(self): self._hasSelection = False

    @Slot("QVariantList")
    def replace(self, ids):
        self._hasSelection = True
        self._count = len(ids)


class TestLibrarySearchPlay:
    def test_search_then_select_then_play(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library/LibraryPage.qml"))
        lb = FakeLibraryBridge()
        sc = FakeSelectionController()
        h.register_doubles({"libraryBridge": lb, "selectionContextBridge": sc,
                            "notificationBridge": QObject(), "actionRegistry": QObject()})
        h.load()

        lb.search("test_song")
        assert lb._searchQuery == "test_song"

        sc.replace([1, 2, 3])
        assert sc._count == 3

        result = lb.playTrackById(1)
        assert result["ok"] is True
        lb._playback_ctrl.play.assert_called_with(1)

        lb.clearFilters()
        assert lb._searchQuery == ""

        h.teardown()

    def test_search_empty_then_clear(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library/LibraryPage.qml"))
        lb = FakeLibraryBridge()
        sc = FakeSelectionController()
        h.register_doubles({"libraryBridge": lb, "selectionContextBridge": sc,
                            "notificationBridge": QObject(), "actionRegistry": QObject()})
        h.load()

        lb.search("nonexistent")
        assert lb._searchQuery == "nonexistent"
        lb.clearFilters()
        assert lb._searchQuery == ""

        h.teardown()

    def test_select_then_context_menu_play(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library/LibraryPage.qml"))
        lb = FakeLibraryBridge()
        sc = FakeSelectionController()
        h.register_doubles({"libraryBridge": lb, "selectionContextBridge": sc,
                            "notificationBridge": QObject(), "actionRegistry": QObject()})
        h.load()

        sc.replace([5])
        result = lb.playTrackById(5)
        assert result["ok"] is True
        lb._playback_ctrl.play.assert_called_with(5)

        h.teardown()
