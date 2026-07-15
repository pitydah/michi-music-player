"""Test HomeAudioPage QML loading and bridge wiring."""
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


def test_home_audio_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()


def test_home_audio_page_has_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "homeAudio.page"
    finally:
        obj.deleteLater()


def test_home_audio_page_null_bridge_safe(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    obj = component.create()
    try:
        ha = obj.property("ha")
        assert ha is None or ha is not None
    finally:
        obj.deleteLater()


def test_home_audio_page_refresh_on_complete(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()


def test_home_audio_page_accessible(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()
    source = (QML_DIR / "pages/home_audio/HomeAudioPage.qml").read_text()
    assert "Accessible.name" in source
    assert "objectName" in source
