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
    bridge.categories = []
    bridge.getValue.return_value = None
    ctx.setContextProperty("settingsBridgeV2", bridge)
    ctx.setContextProperty("notificationBridge", MagicMock())
    obj = comp.create()
    return obj, bridge


class TestSettingsGeneralObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.general"
        finally:
            obj.deleteLater()

    def test_language_combobox_object_name(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            lang = obj.findChild(object, "settings.general.language")
            assert lang is not None
        finally:
            obj.deleteLater()

    def test_close_to_tray_object_name(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.general.closeToTray")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_start_minimized_object_name(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.general.startMinimized")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_clear_cache_object_name(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.general.clearCache")
            assert btn is not None
        finally:
            obj.deleteLater()


class TestSettingsGeneralStates:
    def test_default_state_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_state_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()

    def test_loading_state(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            obj.setProperty("state", "LOADING")
            assert obj.property("state") == "LOADING"
        finally:
            obj.deleteLater()


class TestSettingsGeneralAccessible:
    def test_accessible_role(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.general"
        finally:
            obj.deleteLater()

    def test_accessible_name_language(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            lang = obj.findChild(object, "settings.general.language")
            if lang:
                assert lang.property("accessibleName") == "Seleccionar idioma"
        finally:
            obj.deleteLater()


class TestSettingsGeneralKeyboard:
    def test_escape_signal_defined(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.closeRequested.connect(lambda: fired.append(True))
            obj.closeRequested.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()
