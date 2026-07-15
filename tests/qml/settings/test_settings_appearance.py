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
    bridge.accentColor = "#8FB7FF"
    bridge.reduceMotion = False
    bridge.compactMode = False
    bridge.highContrast = False
    bridge.fontScale = "normal"
    ctx.setContextProperty("themeBridge", bridge)
    obj = comp.create()
    return obj, bridge


class TestSettingsAppearanceObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.appearance"
        finally:
            obj.deleteLater()

    def test_reduce_motion_object_name(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.reduceMotion")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_compact_mode_object_name(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.compactMode")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_cover_backdrop_object_name(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.coverBackdrop")
            assert sw is not None
        finally:
            obj.deleteLater()


class TestSettingsAppearanceStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


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
