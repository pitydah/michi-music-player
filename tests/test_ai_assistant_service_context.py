"""Tests: AIAssistantService receives context_service, uses it safely."""

from unittest.mock import MagicMock
from integrations.ai_assistant.service import AIAssistantService


class TestAiAssistantServiceContext:
    def test_accepts_context_service(self):
        svc = MagicMock()
        assistant = AIAssistantService(db=MagicMock(), context_service=svc)
        assert assistant._context_svc is svc

    def test_defaults_to_none(self):
        assistant = AIAssistantService(db=MagicMock())
        assert assistant._context_svc is None

    def test_inject_context_skips_without_service(self):
        from integrations.ai_assistant.service import _inject_context_snapshot
        msgs = [{"role": "user", "content": "hi"}]
        result = _inject_context_snapshot(msgs, None)
        assert result == msgs
