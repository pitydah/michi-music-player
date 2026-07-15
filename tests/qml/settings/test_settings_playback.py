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


class TestSettingsPlaybackObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.playback"
        finally:
            obj.deleteLater()

    def test_output_device_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.playback.outputDevice")
            assert combo is not None
        finally:
            obj.deleteLater()

    def test_gapless_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.playback.gapless")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_crossfade_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.playback.crossfade")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_replaygain_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.playback.replaygainMode")
            assert combo is not None
        finally:
            obj.deleteLater()

    def test_buffer_size_object_name(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            spin = obj.findChild(object, "settings.playback.bufferSize")
            assert spin is not None
        finally:
            obj.deleteLater()


class TestSettingsPlaybackStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


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
