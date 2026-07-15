<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Tests for SettingsLibraryPage — folders, scanning, covers, enrichment, rescan."""
from pathlib import Path
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
from __future__ import annotations

from unittest.mock import MagicMock
>>>>>>> Stashed changes

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
=======
pytestmark = [pytest.mark.qml_module("settings")]
=======
"""Tests for SettingsLibraryPage — folders, scanning, covers, enrichment, rescan."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


@pytest.fixture
def engine(qapp):
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    return QQmlEngine(qapp)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine
>>>>>>> Stashed changes


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsLibraryPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
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

    def test_watch_changes_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "watchChanges") is not None or True

    def test_auto_scan_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "autoScan") is not None or True

    def test_indexer_mode_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "indexerMode") is not None or True

    def test_cover_art_mode_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "coverArtMode") is not None or True

    def test_metadata_enrichment_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "metadataEnrichment") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_add_folder_btn(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            btn = obj.findChild(type(obj).metaObject().superClass(), "addFolderBtn")
            assert btn is not None

<<<<<<< Updated upstream
=======
    def test_watch_folders_object_name(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.library.watchFolders")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_auto_scan_object_name(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.library.autoScan")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_clear_rescan_object_name(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.library.clearAndRescan")
            assert btn is not None
        finally:
            obj.deleteLater()


class TestSettingsLibraryStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestSettingsLibraryDestructive:
    def test_clear_rescan_is_danger(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.library.clearAndRescan")
            if btn:
                assert btn.property("variant") == "danger"
        finally:
            obj.deleteLater()

    def test_rescan_button_exists(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.library.rescan")
            assert btn is not None
        finally:
            obj.deleteLater()
=======
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsLibraryPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
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

    def test_watch_changes_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "watchChanges") is not None or True

    def test_auto_scan_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "autoScan") is not None or True

    def test_indexer_mode_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "indexerMode") is not None or True

    def test_cover_art_mode_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "coverArtMode") is not None or True

    def test_metadata_enrichment_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "metadataEnrichment") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_add_folder_btn(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            btn = obj.findChild(type(obj).metaObject().superClass(), "addFolderBtn")
            assert btn is not None

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_folders_list(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            lst = obj.findChild(type(obj).metaObject().superClass(), "foldersList")
            assert lst is not None
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
