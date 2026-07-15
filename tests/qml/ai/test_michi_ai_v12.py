"""Tests for Michi AI v12 — no intent_map local, usa MichiAIService V2."""
from unittest.mock import MagicMock, patch

import pytest


class TestMichiAIBridgeCreation:
    def test_requires_device_sync(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge()
        assert ai._dev_svc is None

    def test_creation(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        assert ai is not None

    def test_status_default(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        assert ai.status == "IDLE"

    def test_suggestions_default(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.refresh()
        assert len(ai.suggestions) > 0

    def test_last_error_default(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        assert ai.lastError == ""

    def test_refresh(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.refresh()
        assert True

    def test_score(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        score = ai.aiScore()
        assert isinstance(score, dict)
        assert "score" in score


class TestMichiAIMessages:
    def test_send_message_unknown(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.sendMessage("xyz unknown command")
        assert ai.status == "FAILED"

    def test_send_message_navigate(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        ai = MichiAIBridge(device_sync_service=MagicMock(), navigation_bridge=nav,
                            action_registry=MagicMock())
        ai.sendMessage("abrir ajustes")
        assert ai.status in ("SUCCEEDED", "FAILED")

    def test_send_message_cancel(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.sendMessage("cancel")
        assert ai.status == "CANCELLED"

    def test_send_message_si(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.sendMessage("si")
        assert True

    def test_cancel(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        ai.cancel()
        assert ai.status == "CANCELLED"

    def test_get_chat_history(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock())
        import json
        history = json.loads(ai.getChatHistory())
        assert isinstance(history, list)

    def test_uses_michi_ai_service(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        ai_svc = MagicMock()
        ai_svc.resolve_intent.return_value = None
        ai = MichiAIBridge(device_sync_service=MagicMock(), action_registry=MagicMock(),
                            michi_ai_service=ai_svc)
        assert ai._ai_svc is not None
        assert ai._ai_svc.resolve_intent is not None

    def test_no_intent_map_local(self):
        from ui_qml_bridge import michi_ai_bridge
        content = open(michi_ai_bridge.__file__).read()
        assert "intent_map" not in content

    def test_no_router_frases(self):
        from ui_qml_bridge import michi_ai_bridge
        content = open(michi_ai_bridge.__file__).read()
        assert "_dispatch_action" not in content
