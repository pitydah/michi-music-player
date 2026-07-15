"""Integration tests for AssistantPage (Michi AI) UI."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("michi_ai")]


class TestAssistantPage:
    """Verify AssistantPage loads, states, accessible props, null bridge, keyboard."""

    PAGE_QML = "ui_qml/pages/assistant/AssistantPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "assistant.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Michi AI"
        assert page.property("accessible_description") == "Asistente inteligente para tu ecosistema musical"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("ai") is None
        assert page.property("pageState") == "UNAVAILABLE"

    def test_bridge_connected(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "michiAiBridge": bridge
        })
        assert page.property("ai") is not None

    def test_initialization_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("pageState") in ("INITIALIZING", "UNAVAILABLE")

    def test_set_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setState("TEST")
        assert page.property("pageState") == "TEST"

    def test_set_execution_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setExecutionState("EXECUTING")
        assert page.property("executionState") == "EXECUTING"

    def test_send_message_empty(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.sendMessage()

    def test_cancel_execution_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.cancelExecution()
        assert page.property("executionState") == "REJECTED"
        assert page.property("pageState") == "READY"

    def test_confirm_action_no_pending(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.confirmAction()

    def test_reject_action(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.rejectAction()
        assert page.property("pageState") == "READY"

    def test_retry_action(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.retryAction()
        assert page.property("executionState") == "EXECUTING"
        assert page.property("pageState") == "LOADING"

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_escape_cancels_execution(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setExecutionState("EXECUTING")
        page.event("keyPress", {"key": 16777216})
