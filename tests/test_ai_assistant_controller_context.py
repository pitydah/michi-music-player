"""Tests: AiAssistantController uses set_context_service, not self._win."""

from unittest.mock import MagicMock
from ui.controllers.ai_assistant_controller import AiAssistantController


class TestAiAssistantControllerContext:
    def test_accepts_context_service(self):
        ctrl = AiAssistantController(db=MagicMock())
        svc = MagicMock()
        ctrl.set_context_service(svc)
        assert ctrl._context_svc is svc

    def test_no_win_attribute(self):
        ctrl = AiAssistantController(db=MagicMock())
        assert not hasattr(ctrl, '_win')
