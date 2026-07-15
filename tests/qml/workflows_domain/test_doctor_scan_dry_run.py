from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("library_doctor"), pytest.mark.qml_workflow("scan_dry_run")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeLibraryDoctorBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = MagicMock()
        self._service.scan = MagicMock(return_value={"ok": True, "issues": [{"id": 1, "severity": "warning"}]})
        self._service.dryRun = MagicMock(return_value={"ok": True, "preview": "Fix preview"})
        self._service.repair = MagicMock(return_value={"ok": True, "fixed": 1})

    @Slot(result=dict)
    def scan(self):
        result = self._service.scan()
        self.dataChanged.emit()
        return result

    @Slot(result=dict)
    def dryRun(self):
        result = self._service.dryRun()
        self.dataChanged.emit()
        return result

    @Slot(result=dict)
    def repair(self):
        result = self._service.repair()
        self.dataChanged.emit()
        return result

    @Slot()
    def refresh(self): self.dataChanged.emit()


class TestDoctorScanDryRun:
    def test_scan_then_dry_run_then_confirm(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library_doctor/LibraryDoctorPage.qml"))
        db = FakeLibraryDoctorBridge()
        h.register_doubles({"libraryDoctorBridge": db, "notificationBridge": QObject()})
        h.load()

        result = db.scan()
        assert result["ok"] is True
        assert len(result["issues"]) == 1

        result = db.dryRun()
        assert result["ok"] is True
        assert result["preview"] == "Fix preview"

        result = db.repair()
        assert result["ok"] is True
        assert result["fixed"] == 1

        h.teardown()

    def test_scan_empty_library(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/library_doctor/LibraryDoctorPage.qml"))
        db = FakeLibraryDoctorBridge()
        db._service.scan = MagicMock(return_value={"ok": True, "issues": []})
        h.register_doubles({"libraryDoctorBridge": db, "notificationBridge": QObject()})
        h.load()

        result = db.scan()
        assert result["ok"] is True
        assert len(result["issues"]) == 0

        h.teardown()
