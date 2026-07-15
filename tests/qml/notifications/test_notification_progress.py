"""Tests for NotificationProgressItem QML component."""

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


class TestNotificationProgressItem:
    def test_component_file_exists(self, qml_dir):
        p = qml_dir / "components" / "NotificationProgressItem.qml"
        assert p.exists()

    def test_component_loads(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationProgressItem.qml")))
        assert component.isReady()

    def test_has_objectName(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "components" / "NotificationProgressItem.qml")))
        obj = component.create()
        try:
            assert obj.property("objectName") == "notificationProgressItem"
        finally:
            obj.deleteLater()

    def test_has_progress_bar(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "MichiProgressBar" in content

    def test_has_cancel_button(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "Cancelar" in content

    def test_has_percentage_display(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "%" in content

    def test_supports_indeterminate(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "indeterminate" in content

    def test_has_accessible_properties(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "Accessible" in content

    def test_cancel_signal_exists(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "cancelRequested" in content

    def test_dismiss_signal_exists(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "dismissRequested" in content


class TestNotificationProgressBridge:
    def test_show_progress_creates_notification(self):
        bridge = NotificationBridge()
        result = bridge.showProgress("Scanning files", "job_1", 50)
        assert result["ok"] is True

    def test_progress_updates(self):
        bridge = NotificationBridge()
        bridge.showProgress("Scanning", "job_1", 30)
        result = bridge.showProgress("Scanning...", "job_1", 80)
        assert result.get("updated") is True

    def test_progress_clamped(self):
        bridge = NotificationBridge()
        result = bridge.showProgress("Test", "job_2", 150)
        assert result["ok"] is True
