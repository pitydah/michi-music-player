from __future__ import annotations
from __future__ import annotations
"""Test keyboard navigation through notifications in NotificationBridge.
Tests logical keyboard navigation patterns (next/prev, escape, enter)
applied through bridge methods that keyboard events would trigger.
"""

from unittest.mock import MagicMock
"""Tests for keyboard navigation in notification components."""

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge


@pytest.fixture
def bridge():
    return NotificationBridge()


@pytest.fixture
def mock_registry():
    r = MagicMock()
    r.execute.return_value = {"ok": True}
    return r


class TestKeyboardNavigation:
    def test_enter_executes_current_action(self, mock_registry):
        b = NotificationBridge(action_registry=mock_registry)
        b.showAction("Abrir ajustes", "navigate_settings")
        result = b.executeCurrentAction()
        assert result["ok"] is True

    def test_enter_no_action_returns_false(self, bridge):
        bridge.showMessage("Mensaje sin accion")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_enter_no_current_returns_error(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False
        assert result["error"] == "NO_CURRENT_NOTIFICATION"

    def test_escape_dismisses_current(self, bridge):
        bridge.showMessage("Dismiss con Escape")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_escape_does_nothing_on_empty(self, bridge):
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_next_notification_after_enter_and_dismiss(self, mock_registry):
        b = NotificationBridge(action_registry=mock_registry)
        b.showMessage("First")
        b.showAction("Second con accion", "navigate_home")
        b.dismiss()
        assert b.currentNotification is not None
        result = b.executeCurrentAction()
        assert result["ok"] is True

    def test_notification_item_has_keynav(self, qml_dir):
        content = (qml_dir / "components" / "NotificationItem.qml").read_text()
        assert "Keys" in content
"""Test keyboard navigation through notifications in NotificationBridge.

Tests logical keyboard navigation patterns (next/prev, escape, enter)
applied through bridge methods that keyboard events would trigger.
"""


import pytest


@pytest.fixture
def bridge():
    return NotificationBridge()


@pytest.fixture
def mock_registry():
    r = MagicMock()
    r.execute.return_value = {"ok": True}
    return r


class TestKeyboardNavigation:
    def test_enter_executes_current_action(self, mock_registry):
        b = NotificationBridge(action_registry=mock_registry)
        b.showAction("Abrir ajustes", "navigate_settings")
        result = b.executeCurrentAction()
        assert result["ok"] is True

    def test_enter_no_action_returns_false(self, bridge):
        bridge.showMessage("Mensaje sin accion")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_enter_no_current_returns_error(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False
        assert result["error"] == "NO_CURRENT_NOTIFICATION"

    def test_escape_dismisses_current(self, bridge):
        bridge.showMessage("Dismiss con Escape")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_escape_does_nothing_on_empty(self, bridge):
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_next_notification_after_enter_and_dismiss(self, mock_registry):
        b = NotificationBridge(action_registry=mock_registry)
        b.showMessage("First")
        b.showAction("Second con accion", "navigate_home")
        b.dismiss()
        assert b.currentNotification is not None
        result = b.executeCurrentAction()
        assert result["ok"] is True

    def test_drain_queue_with_escape(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")

        for _ in range(3):
            if bridge.currentNotification:
                bridge.dismiss()
            else:
                break

        assert bridge.currentNotification is None

    def test_focus_navigation_between_items(self, bridge):
        bridge.showMessage("Item A")
        bridge.showMessage("Item B")
        bridge.showMessage("Item C")
        assert bridge.queueLength == 2
        assert bridge.currentNotification is not None

    def test_execute_action_by_id_from_queue(self, mock_registry):
        b = NotificationBridge(action_registry=mock_registry)
        b.showAction("Actionable", "navigate_diagnostics")
        nid = b.currentNotification["id"]
        result = b.executeNotificationAction(str(nid))
        assert result["ok"] is True

    def test_execute_action_by_id_not_found(self, bridge):
        result = bridge.executeNotificationAction("nonexistent")
        assert result["ok"] is False
