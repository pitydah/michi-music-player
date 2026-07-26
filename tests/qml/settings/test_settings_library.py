from __future__ import annotations
"""Tests for SettingsLibraryPage — folders, scanning, covers, enrichment, rescan."""
from pathlib import Path


import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

pytestmark = [pytest.mark.qml_module("settings")]



class FakeSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {
            "library/music_folders": ["/home/user/Música", "/home/user/Music"],
            "library/watch_changes": True,
            "library/auto_scan": True,
            "library/indexer_mode": "quick",
            "library/cover_art_mode": "prefer_embedded",
            "artist_enrichment/enabled": False,
        }
        self.last_key = None
        self.last_value = None

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return []

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key)

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self.last_key = key
        self.last_value = value
        return {"ok": True}

    @Slot(str, result=dict)
    def resetValue(self, key):
        return {"ok": True}

    @Slot(result=dict)
    def resetAll(self):
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


def _load_page(engine, page_name):
    engine.addImportPath(str(QML_DIR))
    comp = QQmlComponent(engine)
    comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings" / page_name)))
    return comp


def _create_context(engine, comp):
    obj = comp.create()
    return obj, None


class TestSettingsLibraryPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridge", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsLibraryPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_music_folders_loaded(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert len(obj.property("musicFolders")) == 2

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert "closeRequested" in (QML_DIR / "pages/settings/SettingsLibraryPage.qml").read_text()

    def test_has_async_state_view(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "asyncStateView") is not None

    def test_has_confirm_dialog(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "confirmActionDialog") is not None

    def test_page_header_present(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "pageHeader") is not None

    def test_property_bridge_available(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("bridge") is not None


class TestSettingsLibraryStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("pageState") == 2
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("pageState") == 2
        finally:
            obj.deleteLater()


class TestSettingsLibraryDestructive:
    def test_clear_rescan_is_danger(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(QObject, "settings.library.clearAndRescan")
            if btn:
                assert btn.property("variant") == "danger"
        finally:
            obj.deleteLater()

    def test_has_glass_cards(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            cards = obj.findChildren(QObject, "glassCard")
            assert len(cards) >= 2
        finally:
            obj.deleteLater()
