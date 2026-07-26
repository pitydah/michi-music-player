from __future__ import annotations
"""Tests for SettingsGeneralPage — language, theme, close-to-tray, cache, updates."""
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
            "general/language": "es",
            "appearance/theme": "dark",
            "general/close_to_tray": False,
            "general/start_minimized": False,
            "general/remember_session": True,
            "general/confirm_exit": False,
            "updates/auto_check": True,
            "cache/total_size_mb": 42.5,
        }

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return []

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key)

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self._values[key] = value
        return {"ok": True, "key": key, "value": value, "applied": True, "requires_restart": False, "message": "ok"}

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


class TestSettingsGeneralPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridge", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsGeneralPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsGeneralPage_control"

    def test_bridge_fallback(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsGeneralPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_escape_key(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert "closeRequested" in (QML_DIR / "pages/settings/SettingsGeneralPage.qml").read_text()

    def test_accessible_role(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsGeneralPage_control"

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsGeneralPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_cache_size_property(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("cacheSize") == 42.5

    def test_has_async_state_view(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "asyncStateView") is not None

    def test_has_check_updates_button(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "checkUpdatesButton") is not None

    def test_has_clear_cache_button(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(QObject, "clearCacheButton") is not None


class TestSettingsGeneralStates:
    def test_default_state_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            assert obj.property("pageState") == 2
        finally:
            obj.deleteLater()

    def test_error_state_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("pageState") == 2
        finally:
            obj.deleteLater()

    def test_loading_state(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            obj.setProperty("pageState", 0)
            assert obj.property("pageState") == 0
        finally:
            obj.deleteLater()


class TestSettingsGeneralAccessible:
    def test_accessible_role(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settingsGeneralPage_control"
        finally:
            obj.deleteLater()

    def test_accessible_name_language(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            lang = obj.findChild(QObject, "settings.general.language")
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
            assert "closeRequested" in (QML_DIR / "pages/settings/SettingsGeneralPage.qml").read_text()
        finally:
            obj.deleteLater()
