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
    sources_bridge = MagicMock()
    sources_bridge.sources = []
    ctx.setContextProperty("settingsBridgeV2", bridge)
    ctx.setContextProperty("librarySourcesBridge", sources_bridge)
    obj = comp.create()
    return obj, bridge, sources_bridge


class TestSettingsLibraryObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.library"
        finally:
            obj.deleteLater()

    def test_add_folder_object_name(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()
        obj, _, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.library.addFolder")
            assert btn is not None
        finally:
            obj.deleteLater()

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
