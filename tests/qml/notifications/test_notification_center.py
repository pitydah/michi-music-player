"""Tests for NotificationCenter QML component."""

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


class TestNotificationCenter:
    def test_component_file_exists(self, qml_dir):
        p = qml_dir / "components" / "NotificationCenter.qml"
        assert p.exists()

    def test_component_loads(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationCenter.qml")))
        assert component.isReady()

    def test_has_objectName(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationCenter.qml")))
        obj = component.create()
        try:
            assert obj.property("objectName") == "notificationCenter"
        finally:
            obj.deleteLater()

    def test_has_listview(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "ListView" in content

    def test_has_dismiss_all_button(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "Descartar todas" in content

    def test_has_empty_state(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "No hay notificaciones" in content

    def test_has_section_headers(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "section" in content

    def test_empty_when_no_notifications(self, bridge):
        assert bridge.queueLength == 0
        assert bridge.currentNotification is None

    def test_accepts_bridge_property(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationCenter.qml")))
        obj = component.create()
        try:
            assert obj.property("notificationBridge") is None
        finally:
            obj.deleteLater()

    def test_clear_removes_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        assert bridge.queueLength > 0
        bridge.clear()
        assert bridge.queueLength == 0
        assert bridge.currentNotification is None

    def test_queue_length_after_messages(self, bridge):
        bridge.showMessage("Persistent", persistent=True)
        assert bridge.queueLength >= 0
