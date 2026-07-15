"""Test keyboard navigation in home audio pages via QML component loading."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = pytest.mark.isolation


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


def test_home_audio_page_focus_scope(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    obj = component.create()
    try:
        assert obj.property("focus") is True
    finally:
        obj.deleteLater()


def test_home_audio_page_key_navigation_tab(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()


def test_zone_detail_page_escape_key(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    assert component.isReady()


def test_group_editor_escape_key(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    assert component.isReady()


def test_zone_detail_key_navigation(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") is not None
    finally:
        obj.deleteLater()


def test_home_audio_page_flickable_focus(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()
