from __future__ import annotations

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
    obj = comp.create()
    return obj


class TestSettingsAboutObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.about"
        finally:
            obj.deleteLater()

    def test_check_updates_object_name(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.about.checkUpdates")
            assert btn is not None
        finally:
            obj.deleteLater()

    def test_close_object_name(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.about.close")
            assert btn is not None
        finally:
            obj.deleteLater()


class TestSettingsAboutStates:
    def test_default_state_ready(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()


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
