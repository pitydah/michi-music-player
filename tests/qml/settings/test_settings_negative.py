from __future__ import annotations

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


class TestSettingsGeneralNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
            assert obj.property("bridge") is None or obj.property("bridge") is None
        finally:
            obj.deleteLater()

    def test_no_bridge_no_crash_on_toggle(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            sw = obj.findChild(object, "settings.general.closeToTray")
            if sw:
                sw.setProperty("checked", True)
        finally:
            obj.deleteLater()


class TestSettingsAppearanceNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestSettingsPlaybackNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()

    def test_no_bridge_no_crash_on_volume(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            slider = obj.findChild(object, "settings.playback.volume")
            if slider:
                slider.setProperty("value", 50)
        finally:
            obj.deleteLater()


class TestSettingsLibraryNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestSettingsAccessibilityNullBridge:
    def test_no_bridge_no_crash(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("objectName") == "settings.accessibility"
        finally:
            obj.deleteLater()


class TestSettingsAudioNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestSettingsAboutNullBridge:
    def test_no_bridge_no_crash(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("objectName") == "settings.about"
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()


class TestSettingsPageCompiles:
    def test_general_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()

    def test_appearance_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()

    def test_playback_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()

    def test_library_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()

    def test_accessibility_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()

    def test_audio_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()

    def test_about_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
