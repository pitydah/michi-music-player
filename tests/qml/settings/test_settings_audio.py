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
    ctx.setContextProperty("settingsBridgeV2", bridge)
    obj = comp.create()
    return obj, bridge


class TestSettingsAudioObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.audio"
        finally:
            obj.deleteLater()

    def test_output_device_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.audio.outputDevice")
            assert combo is not None
        finally:
            obj.deleteLater()

    def test_sample_rate_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.audio.sampleRate")
            assert combo is not None
        finally:
            obj.deleteLater()

    def test_bit_depth_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.audio.bitDepth")
            assert combo is not None
        finally:
            obj.deleteLater()

    def test_buffer_size_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            spin = obj.findChild(object, "settings.audio.bufferSize")
            assert spin is not None
        finally:
            obj.deleteLater()

    def test_expert_mode_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.audio.expertMode")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_diagnostics_object_name(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.audio.diagnostics")
            assert btn is not None
        finally:
            obj.deleteLater()


class TestSettingsAudioStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


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
