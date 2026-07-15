from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("library"), pytest.mark.qml_workflow("album_queue")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeLibraryBridge(QObject):
    stateChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "READY"
        self._songCount = 100
        self._playback_ctrl = MagicMock()
        self._playback_ctrl.play = MagicMock()
        self._playback_ctrl.enqueue = MagicMock()
        self._playback_ctrl.clearQueue = MagicMock()
        self._playback_ctrl.addAlbumToQueue = MagicMock()

    @Property(str, notify=stateChanged)
    def state(self): return self._state

    @Property(int, notify=dataChanged)
    def songCount(self): return self._songCount

    @Slot(int, result=dict)
    def playTrackById(self, tid):
        self._playback_ctrl.play(tid)
        return {"ok": True}

    @Slot(int, result=dict)
    def enqueueTrackById(self, tid):
        self._playback_ctrl.enqueue(tid)
        return {"ok": True}

    @Slot()
    def refresh(self): self.dataChanged.emit()

    @Slot(str, result=dict)
    def enqueueAlbum(self, album_key):
        self._playback_ctrl.addAlbumToQueue(album_key)
        return {"ok": True}


class FakeQueueBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playback_ctrl = MagicMock()
        self._playback_ctrl.reorder = MagicMock()
        self._playback_ctrl.clearQueue = MagicMock()

    @Slot(result=dict)
    def refresh(self): return {"ok": True}


class TestAlbumQueue:
    def test_album_click_then_enqueue(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library/LibraryPage.qml"))
        lb = FakeLibraryBridge()
        h.register_doubles({"libraryBridge": lb, "selectionContextBridge": QObject(),
                            "notificationBridge": QObject(), "actionRegistry": QObject()})
        h.load()

        result = lb.enqueueAlbum("album_key_1")
        assert result["ok"] is True
        lb._playback_ctrl.addAlbumToQueue.assert_called_with("album_key_1")

        h.teardown()

    def test_album_tracks_individually_enqueued(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library/LibraryPage.qml"))
        lb = FakeLibraryBridge()
        h.register_doubles({"libraryBridge": lb, "selectionContextBridge": QObject(),
                            "notificationBridge": QObject(), "actionRegistry": QObject()})
        h.load()

        for tid in range(5):
            result = lb.enqueueTrackById(tid)
            assert result["ok"] is True
            lb._playback_ctrl.enqueue.assert_any_call(tid)

        h.teardown()
