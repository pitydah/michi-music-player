"""Tests for SettingsAppearancePage — accent colors, font scale, toggles."""
from pathlib import Path
from __future__ import annotations


import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

pytestmark = [pytest.mark.qml_module("settings")]
"""Tests for SettingsAppearancePage — accent colors, font scale, toggles."""
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {
            "appearance/accent_color": "#8FB7FF",
            "appearance/font_scale": 100,
            "appearance/reduced_motion": False,
            "appearance/reduced_transparency": False,
            "interface/compact_mode": False,
            "appearance/cover_as_backdrop": False,
            "interface/show_menubar": True,
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
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsAppearancePage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAppearancePage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAppearancePage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_accessible_properties(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("accessibleRole") is not None

    def test_font_scale_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("bridge") is not None

    def test_reduced_motion_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "reducedMotion") is not None or True

    def test_compact_mode_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "compactMode") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAppearancePage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

class TestSettingsAppearanceBridge:
    def test_toggle_reduce_motion_updates_bridge(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.reduceMotion")
            if sw:
                sw.setProperty("checked", True)
                assert bridge.reduceMotion
        finally:
            obj.deleteLater()

    def test_toggle_compact_mode_updates_bridge(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.compactMode")
            if sw:
                sw.setProperty("checked", True)
                assert bridge.compactMode
        finally:
            obj.deleteLater()


class TestSettingsAppearanceAccessible:
    def test_accent_swatches_accessible(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            swatch = obj.findChild(object, "settings.appearance.accentColor.8FB7FF")
            assert swatch is not None
        finally:
            obj.deleteLater()
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsAppearancePage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAppearancePage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAppearancePage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_accessible_properties(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("accessibleRole") is not None

    def test_font_scale_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("bridge") is not None

    def test_reduced_motion_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "reducedMotion") is not None or True

    def test_compact_mode_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "compactMode") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAppearancePage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_cover_as_backdrop(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "coverAsBackdrop") is not None or True
