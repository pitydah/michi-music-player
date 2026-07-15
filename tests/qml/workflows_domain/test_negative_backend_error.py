from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("negative"), pytest.mark.qml_workflow("negative")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeFailingBridge(QObject):
    dataChanged = Signal()

    @Slot(result=dict)
    def refresh(self):
        return {"ok": False, "error": "BACKEND_ERROR: connection refused"}


class FakeSettingsBridge(QObject):
    dataChanged = Signal()
    _categories = []

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._categories

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        return {"ok": False, "error": "BACKEND_ERROR: database locked"}

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()


class TestNegativeBackendError:
    def test_settings_bridge_returns_error(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/SettingsPage.qml"))
        sb = FakeSettingsBridge()
        h.register_doubles({"settingsBridgeV2": sb, "notificationBridge": QObject()})
        h.load()

        result = sb.setValue("general/theme", "dark")
        assert result["ok"] is False
        assert "BACKEND_ERROR" in result.get("error", "")

        h.teardown()

    def test_bridge_refresh_returns_error(self):
        fb = FakeFailingBridge()
        result = fb.refresh()
        assert result["ok"] is False
        assert "BACKEND_ERROR" in result.get("error", "")

    def test_settings_bridge_categories_empty_on_error(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/SettingsPage.qml"))
        sb = FakeSettingsBridge()
        h.register_doubles({"settingsBridgeV2": sb, "notificationBridge": QObject()})
        h.load()

        assert len(sb.categories) == 0

        h.teardown()
