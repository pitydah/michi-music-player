<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test NotificationToast — show, dismiss, auto-dismiss, timer states."""
from __future__ import annotations
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Tests for NotificationToast QML component states and behavior."""
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
"""Test NotificationToast — show, dismiss, auto-dismiss, timer states."""
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
class TestToastShowDismiss:
    def test_show_message_sets_current(self, bridge):
        result = bridge.showMessage("Hola mundo")
        assert result["ok"] is True
        assert bridge.currentNotification is not None
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
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
=======
class TestToastShowDismiss:
    def test_show_message_sets_current(self, bridge):
        result = bridge.showMessage("Hola mundo")
        assert result["ok"] is True
        assert bridge.currentNotification is not None
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        assert bridge.currentNotification["text"] == "Hola mundo"

    def test_dismiss_clears_current(self, bridge):
        bridge.showMessage("Dismiss me")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_show_multiple_queues(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        assert bridge.currentNotification is not None
        assert bridge.queueLength == 1

    def test_dismiss_triggers_next(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        assert bridge.currentNotification["text"] == "First"
        bridge.dismiss()
        assert bridge.currentNotification["text"] == "Second"

    def test_clear_empties_everything(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0


class TestToastTimer:
    def test_non_persistent_has_timeout(self, bridge):
        bridge.showMessage("Normal")
        assert bridge.currentNotification is not None
        assert not bridge.currentNotification.get("persistent", False)

    def test_error_message_is_persistent(self, bridge):
        bridge.showMessage("Error critico", "error")
        assert bridge.currentNotification["persistent"] is True

    def test_action_message_is_persistent(self, bridge):
        bridge.showAction("Accion", "navigate_home")
        assert bridge.currentNotification["persistent"] is True

    def test_dismiss_stops_timer(self, bridge):
        bridge.showMessage("Timed")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_persistent_survives_in_map(self, bridge):
        bridge.showMessage("Error persiste", "error")
        nid = bridge.currentNotification["id"]
        assert nid in bridge._persistent_map


class TestToastKinds:
    def test_info_kind(self, bridge):
        bridge.showMessage("Info", "info")
        assert bridge.currentNotification["kind"] == "info"

    def test_success_kind(self, bridge):
        bridge.showMessage("Exito", "success")
        assert bridge.currentNotification["kind"] == "success"

    def test_warning_kind(self, bridge):
        bridge.showMessage("Advertencia", "warning")
        assert bridge.currentNotification["kind"] == "warning"

    def test_error_kind(self, bridge):
        bridge.showMessage("Error", "error")
        assert bridge.currentNotification["kind"] == "error"

    def test_invalid_kind_falls_back_to_info(self, bridge):
        bridge.showMessage("Raro", "unknown")
        assert bridge.currentNotification["kind"] == "info"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
