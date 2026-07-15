from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("negative"), pytest.mark.qml_workflow("negative")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeBridgeWithConfirm(QObject):
    statusChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"
        self._pending_action = None
        self._rejected = False

    @Property(str, notify=statusChanged)
    def status(self): return self._status

    @Slot(str)
    def sendMessage(self, msg):
        if "borrar" in msg:
            self._pending_action = {"type": "delete", "confirm_required": True}
            self._status = "awaiting_confirmation"
        elif msg == "no" and self._pending_action:
            self._rejected = True
            self._pending_action = None
            self._status = "cancelled"
        elif msg == "sí" and self._pending_action:
            self._pending_action = None
            self._status = "completed"
        self.statusChanged.emit()

    @Slot()
    def cancel(self):
        self._status = "cancelled"
        self.statusChanged.emit()


class TestNegativeRejectedConfirmation:
    def test_reject_destructive_action(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        fb = FakeBridgeWithConfirm()
        h.register_doubles({"michiAIBridge": fb})
        h.load()

        fb.sendMessage("borrar playlist")
        assert fb._status == "awaiting_confirmation"
        assert fb._pending_action is not None

        fb.sendMessage("no")
        assert fb._rejected is True
        assert fb._status == "cancelled"
        assert fb._pending_action is None

        h.teardown()

    def test_confirm_destructive_action(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/assistant/AssistantPage.qml"))
        fb = FakeBridgeWithConfirm()
        h.register_doubles({"michiAIBridge": fb})
        h.load()

        fb.sendMessage("borrar playlist")
        assert fb._status == "awaiting_confirmation"

        fb.sendMessage("sí")
        assert fb._status == "completed"
        assert fb._pending_action is None

        h.teardown()
