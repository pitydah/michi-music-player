from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import pytest
from PySide6.QtCore import QObject, Property, Signal, Slot

import tests.qml.workflows_domain.domain_workflow_harness as harness

pytestmark = [pytest.mark.qml_module("settings"), pytest.mark.qml_workflow("rollback")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {"playback/volume": 80, "general/language": "es"}
        self._snapshot = None
        self._categories = [
            {"id": "playback", "title": "Reproducción", "icon": "play",
             "sections": [{"id": "volume", "title": "Volumen",
                           "entries": [{"key": "playback/volume", "label": "Volumen",
                                        "type": "int", "default": 80}]}]}
        ]

    @Property("QVariantList", notify=dataChanged)
    def categories(self): return self._categories

    @Slot(str, result="QVariant")
    def getValue(self, key): return self._values.get(key)

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self._values[key] = value
        return {"ok": True, "requires_restart": False}

    @Slot(str, result=dict)
    def resetValue(self, key):
        self._values[key] = deepcopy(key)
        return {"ok": True}

    @Slot(result=dict)
    def resetAll(self):
        self._values = {}
        return {"ok": True}

    @Slot()
    def refresh(self): self.dataChanged.emit()


class TestSettingsRollback:
    def test_change_then_reject_then_rollback(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/SettingsPage.qml"))
        sb = FakeSettingsBridge()
        h.register_doubles({"settingsBridgeV2": sb, "notificationBridge": QObject()})
        h.load()

        original = sb.getValue("playback/volume")
        result = sb.setValue("playback/volume", 30)
        assert result["ok"] is True
        assert sb.getValue("playback/volume") == 30

        result = sb.setValue("playback/volume", original)
        assert result["ok"] is True
        assert sb.getValue("playback/volume") == original

        h.teardown()

    def test_reset_all_settings(self):
        h = harness.DomainHarness(QML_DIR, str(QML_DIR / "pages/SettingsPage.qml"))
        sb = FakeSettingsBridge()
        h.register_doubles({"settingsBridgeV2": sb, "notificationBridge": QObject()})
        h.load()

        sb.setValue("playback/volume", 50)
        sb.setValue("general/language", "en")
        assert sb.getValue("playback/volume") == 50
        assert sb.getValue("general/language") == "en"

        result = sb.resetAll()
        assert result["ok"] is True

        h.teardown()
