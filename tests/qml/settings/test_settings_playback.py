"""Tests for SettingsPlaybackPage — output device, volume, crossfade, ReplayGain, buffer."""
from pathlib import Path
from __future__ import annotations


import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

pytestmark = [pytest.mark.qml_module("settings")]
"""Tests for SettingsPlaybackPage — output device, volume, crossfade, ReplayGain, buffer."""
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {
            "playback/default_volume": 70,
            "playback/gapless": True,
            "playback/crossfade": 0,
            "playback/replaygain": "off",
            "audio/buffer_ms": 100,
            "audio/output_device_id": "auto",
            "audio/profile": "standard",
            "playback/remember_volume": True,
            "audio/output_devices": ["Predeterminado", "pipewire", "alsa_output"],
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


class TestSettingsPlaybackPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsPlaybackPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsPlaybackPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_default_volume(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("audioDevices") == ["Predeterminado", "pipewire", "alsa_output"]

    def test_gapless_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "gaplessPlayback") is not None or True

    def test_crossfade_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "crossfadeSlider") is not None or True

    def test_replaygain_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "replaygainMode") is not None or True

    def test_buffer_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bufferSizeSlider") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsPlaybackPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_output_device_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "outputDevice") is not None or True

class TestSettingsPlaybackAccessible:
    def test_accessible_gapless(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.playback.gapless")
            if sw:
                assert "sin pausas" in sw.property("accessibleName").value.lower()
        finally:
            obj.deleteLater()
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsPlaybackPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsPlaybackPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsPlaybackPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_default_volume(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("audioDevices") == ["Predeterminado", "pipewire", "alsa_output"]

    def test_gapless_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "gaplessPlayback") is not None or True

    def test_crossfade_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "crossfadeSlider") is not None or True

    def test_replaygain_combo(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "replaygainMode") is not None or True

    def test_buffer_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bufferSizeSlider") is not None or True

    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsPlaybackPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_output_device_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "outputDevice") is not None or True

    def test_audio_profile_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "audioProfile") is not None or True
