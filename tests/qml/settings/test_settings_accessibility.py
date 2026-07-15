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
    bridge.highContrast = False
    bridge.reduceMotion = False
    bridge.fontScale = "normal"
    ctx.setContextProperty("themeBridge", bridge)
    obj = comp.create()
    return obj, bridge


class TestSettingsAccessibilityObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.accessibility"
        finally:
            obj.deleteLater()

    def test_mono_object_name(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.accessibility.mono")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_balance_object_name(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            slider = obj.findChild(object, "settings.accessibility.balance")
            assert slider is not None
        finally:
            obj.deleteLater()

    def test_high_contrast_object_name(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.accessibility.highContrast")
            assert sw is not None
        finally:
            obj.deleteLater()

    def test_font_scale_object_name(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            combo = obj.findChild(object, "settings.accessibility.fontScale")
            assert combo is not None
        finally:
            obj.deleteLater()


class TestSettingsAccessibilityStates:
    def test_default_state_ready(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()


class TestSettingsAccessibilityBridge:
    def test_toggle_high_contrast_updates_bridge(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.accessibility.highContrast")
            if sw:
                sw.setProperty("checked", True)
                assert bridge.highContrast
        finally:
            obj.deleteLater()

    def test_toggle_reduce_motion_updates_bridge(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.accessibility.reduceMotion")
            if sw:
                sw.setProperty("checked", True)
                assert bridge.reduceMotion
        finally:
            obj.deleteLater()
