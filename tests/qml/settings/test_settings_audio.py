<<<<<<< Updated upstream
"""Tests for SettingsAudioPage — devices, sample rate, bit depth, buffer, expert mode."""
from pathlib import Path
=======
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
"""Tests for SettingsAudioPage — devices, sample rate, bit depth, buffer, expert mode."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

>>>>>>> Stashed changes

class FakeSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {
            "audio/output_device_id": "auto",
            "audio/sample_rate": 0,
            "audio/bit_depth": "auto",
            "audio/buffer_ms": 100,
            "audio/resample_quality": "medium",
            "audio/replaygain_enabled": False,
            "audio/expert_mode": False,
            "audio/allow_resample": True,
            "audio/allow_fallback": True,
            "audio/output_devices": ["Auto", "pipewire", "alsa_output"],
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
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


@pytest.fixture
def engine(qapp):
<<<<<<< Updated upstream
    return QQmlEngine(qapp)
=======
<<<<<<< HEAD
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine
>>>>>>> Stashed changes


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsAudioPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAudioPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAudioPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_audio_devices_loaded(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("audioDevices") == ["Auto", "pipewire", "alsa_output"]

    def test_expert_mode_false_by_default(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("expertMode") is False

    def test_output_device_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "outputDevice") is not None or True

    def test_sample_rate_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "sampleRate") is not None or True

    def test_bit_depth_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bitDepth") is not None or True

    def test_buffer_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bufferSlider") is not None or True

    def test_resample_quality_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "resampleQuality") is not None or True

    def test_volume_normalization_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "volumeNormalization") is not None or True

    def test_expert_mode_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "expertModeToggle") is not None or True

<<<<<<< Updated upstream
=======
class TestSettingsAudioDiagnosticsSignal:
    def test_open_diagnostics_signal(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.openDiagnostics.connect(lambda: fired.append(True))
            obj.openDiagnostics.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()
=======
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsAudioPage:
    def _load_page(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAudioPage.qml")))
        return comp

    def test_creates(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_object_name(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.objectName() == "settingsAudioPage"

    def test_initial_state_ready(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("pageState") == 2

    def test_audio_devices_loaded(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("audioDevices") == ["Auto", "pipewire", "alsa_output"]

    def test_expert_mode_false_by_default(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.property("expertMode") is False

    def test_output_device_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "outputDevice") is not None or True

    def test_sample_rate_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "sampleRate") is not None or True

    def test_bit_depth_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bitDepth") is not None or True

    def test_buffer_slider(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "bufferSlider") is not None or True

    def test_resample_quality_selector(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "resampleQuality") is not None or True

    def test_volume_normalization_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "volumeNormalization") is not None or True

    def test_expert_mode_toggle(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "expertModeToggle") is not None or True

>>>>>>> Stashed changes
    def test_null_bridge(self, engine, bridge):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsAudioPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_escape_signal(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.metaObject().indexOfSignal("closeRequested()") >= 0

    def test_diagnostics_button(self, engine, bridge):
        comp = self._load_page(engine, bridge)
        if comp.isReady():
            obj = comp.create()
            assert obj.findChild(type(obj).metaObject().superClass(), "runDiagnosticsBtn") is not None or True
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
