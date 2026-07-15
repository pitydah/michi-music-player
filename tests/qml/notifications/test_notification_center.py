<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test notification list, dismiss all, empty state logic in NotificationBridge."""
from __future__ import annotations
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Tests for NotificationCenter QML component."""
>>>>>>> Stashed changes

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge

<<<<<<< Updated upstream
=======
QML_DIR = None


@pytest.fixture(scope="module")
def qml_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)

=======
"""Test notification list, dismiss all, empty state logic in NotificationBridge."""
from __future__ import annotations

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge

>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

@pytest.fixture
def bridge():
    return NotificationBridge()


<<<<<<< Updated upstream
<<<<<<< Updated upstream
class TestNotificationList:
    def test_queue_length_starts_zero(self, bridge):
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
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
>>>>>>> Stashed changes
        assert bridge.queueLength == 0

    def test_queue_increases_after_showing(self, bridge):
        bridge.showMessage("First")
        assert bridge.queueLength == 0
        bridge.showMessage("Second")
        assert bridge.queueLength == 1

    def test_dismiss_removes_current_and_pulls_from_queue(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        bridge.dismiss()
        assert bridge.currentNotification["text"] == "Second"
        assert bridge.queueLength == 0

    def test_multiple_dismiss_drains_queue(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.dismiss()
        bridge.dismiss()
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_persistent_notifications_appear_in_map(self, bridge):
        bridge.showMessage("Error test", "error")
        assert len(bridge._persistent_map) == 1

    def test_persistent_map_cleared_on_dismiss(self, bridge):
        bridge.showMessage("Error test", "error")
        nid = bridge.currentNotification["id"]
        assert nid in bridge._persistent_map
        bridge.dismiss()
        assert nid not in bridge._persistent_map


class TestDismissAll:
    def test_clear_removes_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0
        assert len(bridge._persistent_map) == 0

    def test_clear_removes_persistent_too(self, bridge):
        bridge.showMessage("Persistent", "error")
        bridge.showMessage("Normal")
        bridge.clear()
        assert bridge.currentNotification is None
        assert len(bridge._persistent_map) == 0

    def test_clear_does_not_crash_on_empty(self, bridge):
        bridge.clear()
        assert bridge.currentNotification is None

<<<<<<< Updated upstream
=======
    def test_queue_length_after_messages(self, bridge):
        bridge.showMessage("Persistent", persistent=True)
        assert bridge.queueLength >= 0
=======
class TestNotificationList:
    def test_queue_length_starts_zero(self, bridge):
        assert bridge.queueLength == 0

    def test_queue_increases_after_showing(self, bridge):
        bridge.showMessage("First")
        assert bridge.queueLength == 0
        bridge.showMessage("Second")
        assert bridge.queueLength == 1

    def test_dismiss_removes_current_and_pulls_from_queue(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        bridge.dismiss()
        assert bridge.currentNotification["text"] == "Second"
        assert bridge.queueLength == 0

    def test_multiple_dismiss_drains_queue(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.dismiss()
        bridge.dismiss()
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_persistent_notifications_appear_in_map(self, bridge):
        bridge.showMessage("Error test", "error")
        assert len(bridge._persistent_map) == 1

    def test_persistent_map_cleared_on_dismiss(self, bridge):
        bridge.showMessage("Error test", "error")
        nid = bridge.currentNotification["id"]
        assert nid in bridge._persistent_map
        bridge.dismiss()
        assert nid not in bridge._persistent_map


class TestDismissAll:
    def test_clear_removes_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0
        assert len(bridge._persistent_map) == 0

    def test_clear_removes_persistent_too(self, bridge):
        bridge.showMessage("Persistent", "error")
        bridge.showMessage("Normal")
        bridge.clear()
        assert bridge.currentNotification is None
        assert len(bridge._persistent_map) == 0

    def test_clear_does_not_crash_on_empty(self, bridge):
        bridge.clear()
        assert bridge.currentNotification is None

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

class TestEmptyState:
    def test_empty_initially(self, bridge):
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_empty_after_full_drain(self, bridge):
        bridge.showMessage("Temp")
        bridge.dismiss()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_empty_notification_score(self, bridge):
        score = bridge.notificationScore()
        assert score["has_current"] is False
        assert score["queue_length"] == 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
