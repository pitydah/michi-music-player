"""Tests for NotificationToast QML component states and behavior."""

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from ui_qml_bridge.notification_bridge import NotificationBridge

QML_DIR = None


@pytest.fixture(scope="module")
def qml_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return NotificationBridge()


@pytest.fixture
def toast_component(engine, qml_dir):
    engine.addImportPath(str(qml_dir))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationToast.qml")))
    return component


class TestNotificationToastInstantiation:
    def test_component_loads(self, toast_component):
        assert toast_component.isReady()

    def test_has_objectName(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationToast.qml")))
        obj = component.create()
        try:
            assert obj.property("objectName") == "notificationToast"
        finally:
            obj.deleteLater()

    def test_has_accessible_role(self, qml_dir):
        content = (qml_dir / "components" / "NotificationToast.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_has_escape_key_handler(self, qml_dir):
        content = (qml_dir / "components" / "NotificationToast.qml").read_text()
        assert "Keys.onEscapePressed" in content

    def test_slide_animation_exists(self, qml_dir):
        content = (qml_dir / "components" / "NotificationToast.qml").read_text()
        assert "slideAnim" in content or "slideTransform" in content


class TestNotificationToastBridgeIntegration:
    def test_accepts_null_bridge(self, toast_component):
        obj = toast_component.create()
        try:
            bridge = obj.property("notificationBridge")
            assert bridge is None
        finally:
            obj.deleteLater()

    def test_toast_visible_when_current(self, bridge):
        bridge.showMessage("Test message")
        assert bridge.currentNotification is not None
        assert bridge.currentNotification["text"] == "Test message"
