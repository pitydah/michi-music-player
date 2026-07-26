from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


@pytest.fixture
def bridge():
    return MichiAIBridge()


class TestStates:
    def test_initial_state(self, bridge):
        assert bridge.status == "IDLE"

    def test_valid_states(self, bridge):
        for s in ("IDLE", "PLANNING", "CONFIRMATION_REQUIRED",
                  "RUNNING", "CANCELLED", "SUCCEEDED", "FAILED"):
            bridge._set_status(s)
            assert bridge.status == s

    def test_invalid_state_ignored(self, bridge):
        bridge._set_status("bogus")
        assert bridge.status == "IDLE"


class TestActionExecution:
    def test_send_message_fails_without_service(self, bridge):
        bridge.sendMessage("reproduce 42")
        assert bridge.status == "FAILED"

    def test_send_message_unknown_fallback(self, bridge):
        bridge.sendMessage("qué hora es")
        assert len(bridge._chat_history) >= 2

    def test_send_message_cancel(self, bridge):
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"

    def test_send_message_detener(self, bridge):
        bridge.sendMessage("detener")
        assert bridge.status == "CANCELLED"


class TestCancel:
    def test_cancel_sets_cancelled(self, bridge):
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_cancel_idempotent(self, bridge):
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        bridge.cancel()
        assert bridge.status == "CANCELLED"


class TestScore:
    def test_score_no_services(self):
        minimal = MichiAIBridge()
        score = minimal.aiScore()
        assert score["score"] >= 0
        assert score["has_ai_service"] is False

    def test_score_with_michi_ai_service(self):
        svc = MagicMock()
        bridge = MichiAIBridge(michi_ai_service=svc)
        score = bridge.aiScore()
        assert score["has_ai_service"] is True
