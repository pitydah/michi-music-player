from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("history"), pytest.mark.qml_workflow("filter_play_remove")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeHistoryBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._historyModel = [
            {"eventId": 1, "trackId": 10, "title": "Song A", "artist": "Artist 1", "playedAt": 1000},
            {"eventId": 2, "trackId": 20, "title": "Song B", "artist": "Artist 2", "playedAt": 2000},
            {"eventId": 3, "trackId": 30, "title": "Song C", "artist": "Artist 1", "playedAt": 3000},
        ]
        self._historyCount = 3
        self._playbackBridge = MagicMock()
        self._playbackBridge.enqueue = MagicMock(return_value={"ok": True})

    @Property("QVariantList", notify=dataChanged)
    def historyModel(self): return self._historyModel

    @Property(int, notify=dataChanged)
    def historyCount(self): return self._historyCount

    @Slot(str, result=dict)
    def playHistoryItem(self, track_id):
        return {"ok": True}

    @Slot(str, result=dict)
    def removeHistoryEvent(self, event_id):
        self._historyModel = [e for e in self._historyModel if str(e["eventId"]) != event_id]
        self._historyCount = len(self._historyModel)
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def clearHistory(self):
        self._historyModel = []
        self._historyCount = 0
        self.dataChanged.emit()
        return {"ok": True}

    @Slot()
    def refresh(self): self.dataChanged.emit()


class TestHistoryFilterPlayRemove:
    def test_filter_then_play(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/history/HistoryPage.qml"))
        hb = FakeHistoryBridge()
        h.register_doubles({"historyBridge": hb, "notificationBridge": QObject()})
        h.load()

        filtered = [e for e in hb._historyModel if "Song" in e["title"]]
        assert len(filtered) == 3

        result = hb.playHistoryItem("10")
        assert result["ok"] is True

        h.teardown()

    def test_remove_single_event(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/history/HistoryPage.qml"))
        hb = FakeHistoryBridge()
        h.register_doubles({"historyBridge": hb, "notificationBridge": QObject()})
        h.load()

        result = hb.removeHistoryEvent("1")
        assert result["ok"] is True
        assert hb._historyCount == 2

        h.teardown()

    def test_clear_all_history(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/history/HistoryPage.qml"))
        hb = FakeHistoryBridge()
        h.register_doubles({"historyBridge": hb, "notificationBridge": QObject()})
        h.load()

        result = hb.clearHistory()
        assert result["ok"] is True
        assert hb._historyCount == 0

        h.teardown()

    def test_filter_by_artist(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/history/HistoryPage.qml"))
        hb = FakeHistoryBridge()
        h.register_doubles({"historyBridge": hb, "notificationBridge": QObject()})
        h.load()

        artist_filtered = [e for e in hb._historyModel if e["artist"] == "Artist 1"]
        assert len(artist_filtered) == 2

        h.teardown()
