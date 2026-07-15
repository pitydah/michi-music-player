from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("queue"), pytest.mark.qml_workflow("reorder_undo")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeQueueBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = [{"id": i, "title": f"Track {i}"} for i in range(5)]
        self._snapshot_history = []
        self._playback_ctrl = MagicMock()
        self._playback_ctrl.reorder = MagicMock(return_value={"ok": True})
        self._playback_ctrl.snapshotQueue = MagicMock(return_value={"ok": True, "snapshot": "s1"})
        self._playback_ctrl.restoreQueueSnapshot = MagicMock(return_value={"ok": True})

    @Slot(result=dict)
    def refresh(self): return {"ok": True}

    @Slot(int, int, result=dict)
    def moveItem(self, from_idx, to_idx):
        self._playback_ctrl.reorder(from_idx, to_idx)
        self._snapshot_history.append("s1")
        return {"ok": True}

    @Slot(result=dict)
    def undo(self):
        if self._snapshot_history:
            self._snapshot_history.pop()
            self._playback_ctrl.restoreQueueSnapshot("s1")
            return {"ok": True}
        return {"ok": False, "error": "no_history"}


class FakeNowPlayingBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)


class TestQueueReorderUndo:
    def test_reorder_then_undo(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/queue/QueuePage.qml"))
        qb = FakeQueueBridge()
        npb = FakeNowPlayingBridge()
        h.register_doubles({"queueBridge": qb, "nowplayingBridge": npb,
                            "notificationBridge": QObject()})
        h.load()

        result = qb.moveItem(0, 3)
        assert result["ok"] is True
        qb._playback_ctrl.reorder.assert_called_with(0, 3)

        result = qb.undo()
        assert result["ok"] is True
        qb._playback_ctrl.restoreQueueSnapshot.assert_called()

        h.teardown()

    def test_undo_without_history_returns_error(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/queue/QueuePage.qml"))
        qb = FakeQueueBridge()
        h.register_doubles({"queueBridge": qb, "nowplayingBridge": FakeNowPlayingBridge(),
                            "notificationBridge": QObject()})
        h.load()

        qb._snapshot_history.clear()
        result = qb.undo()
        assert result["ok"] is False
        assert "no_history" in result.get("error", "")

        h.teardown()
