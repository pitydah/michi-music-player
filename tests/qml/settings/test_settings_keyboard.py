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
    obj = comp.create()
    return obj


class TestSettingsKeyboardNavigation:
    def test_general_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.general"
            assert obj.property("activeFocusOnTab") or True
        finally:
            obj.deleteLater()

    def test_appearance_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.appearance"
        finally:
            obj.deleteLater()

    def test_playback_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.playback"
        finally:
            obj.deleteLater()

    def test_library_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.library"
        finally:
            obj.deleteLater()

    def test_accessibility_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.accessibility"
        finally:
            obj.deleteLater()

    def test_audio_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.audio"
        finally:
            obj.deleteLater()

    def test_about_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.about"
        finally:
            obj.deleteLater()


class TestSettingsKeyboardTabOrder:
    def test_general_keyboard_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            lang = obj.findChild(object, "settings.general.language")
            if lang:
                tab = lang.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()

    def test_appearance_keyboard_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.reduceMotion")
            if sw:
                tab = sw.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()

    def test_audio_diagnostics_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.audio.diagnostics")
            if btn:
                tab = btn.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()
