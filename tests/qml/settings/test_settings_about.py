from __future__ import annotations
"""Tests for SettingsAboutPage — version, system info, links, dependencies."""
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
            "about/version": "1.0.0",
            "about/os": "Arch Linux 6.12",
            "about/python_version": "3.12.4",
            "about/qt_version": "6.7.2",
            "about/gstreamer_version": "1.28.0",
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


class TestSettingsAboutPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAboutPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAboutPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_system_info_loaded(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("appVersion") == "1.0.0"
            assert obj.property("osInfo") == "Arch Linux 6.12"
            assert obj.property("pythonVersion") == "3.12.4"
            assert obj.property("qtVersion") == "6.7.2"
            assert obj.property("gstreamerVersion") == "1.28.0"

    def test_accessible_properties(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("accessibleRole") is not None

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAboutPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

class TestSettingsAboutSignals:
    def test_check_updates_signal(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            fired = []
            obj.checkUpdates.connect(lambda: fired.append(True))
            obj.checkUpdates.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()

    def test_close_requested_signal(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            fired = []
            obj.closeRequested.connect(lambda: fired.append(True))
            obj.closeRequested.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsAboutPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAboutPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAboutPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_system_info_loaded(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("appVersion") == "1.0.0"
            assert obj.property("osInfo") == "Arch Linux 6.12"
            assert obj.property("pythonVersion") == "3.12.4"
            assert obj.property("qtVersion") == "6.7.2"
            assert obj.property("gstreamerVersion") == "1.28.0"

    def test_accessible_properties(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("accessibleRole") is not None

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAboutPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_check_updates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "updatesCard") is not None
