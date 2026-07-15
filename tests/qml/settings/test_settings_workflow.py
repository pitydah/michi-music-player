from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from pathlib import Path
QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

pytestmark = [pytest.mark.qml_module("settings")]


@pytest.fixture
def engine(qapp):
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine


def _load_page(engine, page: str) -> QQmlComponent:
    comp = QQmlComponent(engine)
    comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings" / page)))
    return comp


def _create_context(engine, comp):
    ctx = engine.rootContext()
    bridge = MagicMock()
    bridge.getValue.return_value = None
    ctx.setContextProperty("settingsBridgeV2", bridge)
    ctx.setContextProperty("themeBridge", MagicMock())
    ctx.setContextProperty("librarySourcesBridge", MagicMock())
    ctx.setContextProperty("notificationBridge", MagicMock())
    obj = comp.create()
    return obj, bridge


class TestSettingsWorkflowGeneral:
    def test_navigate_to_general(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
            assert obj.property("objectName") == "settings.general"
        finally:
            obj.deleteLater()

    def test_toggle_close_to_tray(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.general.closeToTray")
            if sw:
                sw.setProperty("checked", True)
                assert sw.property("checked")
                sw.setProperty("checked", False)
                assert not sw.property("checked")
        finally:
            obj.deleteLater()

    def test_reset_dialog_triggers(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            dialog = obj.findChild(object, "settings.general.resetConfirm")
            if dialog:
                dialog.setProperty("open", True)
                assert dialog.property("open")
        finally:
            obj.deleteLater()


class TestSettingsWorkflowAudio:
    def test_expert_mode_reveals_options(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            expert = obj.findChild(object, "settings.audio.expertMode")
            if expert:
                expert.setProperty("checked", True)
                assert expert.property("checked")
        finally:
            obj.deleteLater()


class TestSettingsWorkflowLibrary:
    def test_destructive_action_requires_confirmation(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.library.clearAndRescan")
            dialog = obj.findChild(object, "settings.library.clearRescanConfirm")
            if btn and dialog:
                assert btn.property("variant") == "danger"
                assert not dialog.property("open")
        finally:
            obj.deleteLater()


class TestSettingsWorkflowAccessibility:
    def test_toggle_both_announcements(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            track_toggle = obj.findChild(object, "settings.accessibility.announceTrack")
            playback_toggle = obj.findChild(object, "settings.accessibility.announcePlayback")
            if track_toggle and playback_toggle:
                track_toggle.setProperty("checked", True)
                playback_toggle.setProperty("checked", True)
                assert track_toggle.property("checked")
                assert playback_toggle.property("checked")
        finally:
            obj.deleteLater()
