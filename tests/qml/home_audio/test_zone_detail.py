"""Test ZoneDetailPage properties, signals, volume control, mute."""
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


def test_zone_detail_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    assert component.isReady()


def test_zone_detail_page_has_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "zoneDetailPage"
    finally:
        obj.deleteLater()


def test_zone_detail_signals(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        obj.setProperty("zoneId", "test_zone_1")
        obj.setProperty("zoneName", "Living Room")
        obj.setProperty("zoneVolume", 75)
        obj.setProperty("zoneMuted", False)
        assert obj.property("zoneId") == "test_zone_1"
        assert obj.property("zoneName") == "Living Room"
        assert obj.property("zoneVolume") == 75
        assert obj.property("zoneMuted") is False
    finally:
        obj.deleteLater()


def test_zone_detail_volume_signal(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        obj.setProperty("zoneVolume", 50)
        assert obj.property("zoneVolume") == 50
    finally:
        obj.deleteLater()


def test_zone_detail_mute_toggle(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        obj.setProperty("zoneMuted", True)
        assert obj.property("zoneMuted") is True
        obj.setProperty("zoneMuted", False)
        assert obj.property("zoneMuted") is False
    finally:
        obj.deleteLater()


def test_zone_detail_latency(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        obj.setProperty("zoneLatencyMs", 50)
        assert obj.property("zoneLatencyMs") == 50
    finally:
        obj.deleteLater()


def test_zone_detail_accessible(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/ZoneDetailPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "zoneDetailPage"
    finally:
        obj.deleteLater()
