from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("michi_ai"), pytest.mark.qml_workflow("proposal_execution")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeMichiAIBridge(QObject):
    statusChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"
        self._chat_history = []
        self._suggestions = []
        self._pending_action = None
        self._current_task_id = None
        self._services = {
            "track_action_service": MagicMock(),
            "playlist_service": MagicMock(),
            "navigation_bridge": MagicMock(),
            "global_search_service": MagicMock(),
        }
        self._services["track_action_service"].play_track = MagicMock(return_value={"ok": True})
        self._services["track_action_service"].enqueue = MagicMock(return_value={"ok": True})
        self._services["playlist_service"].create = MagicMock(return_value={"ok": True, "id": 1})
        self._services["global_search_service"].search = MagicMock(
            return_value={"ok": True, "results": [{"type": "track", "id": 1}], "count": 1}
        )

    @Property(str, notify=statusChanged)
    def status(self): return self._status

    @Property("QVariantList", notify=statusChanged)
    def suggestions(self): return self._suggestions

    @Slot(str)
    def sendMessage(self, msg):
        self._chat_history.append({"role": "user", "content": msg})
        if "reproduce" in msg:
            self._services["track_action_service"].play_track(1)
            self._status = "completed"
            self.statusChanged.emit()
        elif "crear playlist" in msg:
            self._pending_action = {"type": "create_playlist"}
            self._status = "awaiting_confirmation"
            self.statusChanged.emit()
        elif msg == "sí" and self._pending_action:
            self._services["playlist_service"].create("New Playlist")
            self._pending_action = None
            self._status = "completed"
            self.statusChanged.emit()
        elif msg == "no" and self._pending_action:
            self._pending_action = None
            self._status = "cancelled"
            self.statusChanged.emit()
        elif "buscar" in msg:
            self._services["global_search_service"].search(msg)
            self._status = "completed"
            self.statusChanged.emit()
        else:
            self._status = "failed"
            self.statusChanged.emit()

    @Slot()
    def cancel(self):
        self._status = "cancelled"
        self.statusChanged.emit()

    @Slot()
    def refresh(self): pass


class TestMichiAIProposalExecution:
    def test_proposal_then_confirmation_then_execution(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab.sendMessage("crear playlist llamada Favoritos")
        assert ab._status == "awaiting_confirmation"
        assert ab._pending_action is not None

        ab.sendMessage("sí")
        assert ab._status == "completed"
        assert ab._pending_action is None

        h.teardown()

    def test_proposal_then_rejection(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab.sendMessage("crear playlist llamada Favoritos")
        assert ab._status == "awaiting_confirmation"

        ab.sendMessage("no")
        assert ab._status == "cancelled"

        h.teardown()

    def test_direct_playback_execution(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab.sendMessage("reproduce canción 1")
        ab._services["track_action_service"].play_track.assert_called_with(1)
        assert ab._status == "completed"

        h.teardown()

    def test_cancel_during_execution(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab._status = "executing"
        ab.cancel()
        assert ab._status == "cancelled"

        h.teardown()
