from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("negative"), pytest.mark.qml_workflow("negative")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeMichiAIBridge(QObject):
    statusChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"
        self._chat_history = []
        self._pending_action = None

    @Property(str, notify=statusChanged)
    def status(self): return self._status

    @Slot(str)
    def sendMessage(self, msg):
        if "crear" in msg:
            self._pending_action = {"type": "create"}
            self._status = "awaiting_confirmation"
        elif msg == "no":
            self._pending_action = None
            self._status = "cancelled"
        self.statusChanged.emit()

    @Slot()
    def cancel(self):
        self._status = "cancelled"
        self.statusChanged.emit()


class TestNegativeCancellation:
    def test_user_cancels_action(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab.sendMessage("crear playlist")
        assert ab._status == "awaiting_confirmation"

        ab.sendMessage("no")
        assert ab._status == "cancelled"
        assert ab._pending_action is None

        h.teardown()

    def test_explicit_cancel(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        ab = FakeMichiAIBridge()
        h.register_doubles({"michiAIBridge": ab})
        h.load()

        ab.cancel()
        assert ab._status == "cancelled"

        h.teardown()
