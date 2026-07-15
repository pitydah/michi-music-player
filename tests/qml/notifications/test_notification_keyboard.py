"""Tests for keyboard navigation in notification components."""

import pytest
from PySide6.QtQml import QQmlEngine

QML_DIR = None


@pytest.fixture(scope="module")
def qml_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestNotificationKeyboard:
    def test_toast_escape_dismiss(self, qml_dir):
        content = (qml_dir / "components" / "NotificationToast.qml").read_text()
        assert "Keys.onEscapePressed" in content
        assert "dismiss()" in content

    def test_notification_item_enter_activates(self, qml_dir):
        content = (qml_dir / "components" / "NotificationItem.qml").read_text()
        assert "Keys.onReturnPressed" in content
        assert "actionRequested" in content

    def test_notification_center_listview_keynav(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "keyNavigationEnabled" in content
        assert "focus: true" in content

    def test_notification_item_accessible(self, qml_dir):
        content = (qml_dir / "components" / "NotificationItem.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content
        assert "Accessible.description" in content

    def test_notification_center_accessible(self, qml_dir):
        content = (qml_dir / "components" / "NotificationCenter.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_toast_accessible(self, qml_dir):
        content = (qml_dir / "components" / "NotificationToast.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_progress_item_accessible(self, qml_dir):
        content = (qml_dir / "components" / "NotificationProgressItem.qml").read_text()
        assert "Accessible" in content

    def test_banner_accessible(self, qml_dir):
        content = (qml_dir / "components" / "NotificationBanner.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_notification_item_has_keynav(self, qml_dir):
        content = (qml_dir / "components" / "NotificationItem.qml").read_text()
        assert "Keys" in content
