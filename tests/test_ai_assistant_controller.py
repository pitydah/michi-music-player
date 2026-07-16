"""Tests for AiAssistantController."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def ctrl(db):
    from legacy_widgets.ui.controllers.legacy_controllers.ai_assistant_controller import AiAssistantController
    ctrl = AiAssistantController(db=db, worker_manager=None, playback=None,
                                  safe_mode=False)
    ctrl._pending = False
    return ctrl


class TestAiAssistantController:
    def test_init_sets_attributes(self, ctrl, db):
        assert ctrl._db is db
        assert ctrl._pending is False

    def test_is_enabled_returns_false_in_safe_mode(self, ctrl):
        ctrl._safe_mode = True
        assert ctrl.is_enabled() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_is_enabled_returns_true_from_settings(self, ctrl):
        ctrl._safe_mode = False
        with patch("ui.controllers.ai_assistant_controller.get_bool", return_value=True):
            assert ctrl.is_enabled() is True

    def test_model_returns_default(self, ctrl):
        with patch("ui.controllers.ai_assistant_controller.get_str", return_value=""):
            assert ctrl.model() == "llama3.1:8b"

    def test_base_url_returns_default(self, ctrl):
        with patch("ui.controllers.ai_assistant_controller.get_str", return_value=""):
            assert ctrl.base_url() == "http://127.0.0.1:11434"

    def test_check_health_disabled_returns_false(self, ctrl):
        ctrl._safe_mode = True
        assert ctrl.check_health() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_check_health_returns_service_value(self, ctrl):
        ctrl._safe_mode = False
        ctrl._service = MagicMock()
        ctrl._service.ollama_available = True
        with patch("ui.controllers.ai_assistant_controller.get_bool", return_value=True):
            assert ctrl.check_health() is True

    def test_send_message_disabled_emits_disabled_reply(self, ctrl):
        ctrl._safe_mode = True
        results = []
        ctrl.response_received.connect(lambda r: results.append(r))
        ctrl.send_message("hello")
        assert len(results) == 1
        assert "desactivado" in results[0]["reply"]

    def test_send_message_skips_empty(self, ctrl):
        ctrl.send_message("")
        assert ctrl._pending is False

    def test_send_message_skips_when_pending(self, ctrl):
        ctrl._pending = True
        ctrl.send_message("hello")
        assert ctrl._pending is True

    @patch.dict("os.environ", {}, clear=True)
    def test_send_message_with_worker_manager(self, ctrl):
        ctrl._worker_mgr = MagicMock()
        ctrl._safe_mode = False
        with patch("ui.controllers.ai_assistant_controller.get_bool", return_value=True):
            ctrl.send_message("hello")
            ctrl._worker_mgr.run_task.assert_called_once()

    def test_send_message_without_worker_calls_do_process(self, ctrl):
        ctrl._worker_mgr = None
        ctrl._safe_mode = False
        ctrl._service = MagicMock()
        ctrl._service.process_message.return_value = {"reply": "ok"}
        with patch("ui.controllers.ai_assistant_controller.get_bool", return_value=True):
            ctrl.send_message("hello")
            assert ctrl._pending is False

    def test_clear_conversation_calls_service_clear(self, ctrl):
        ctrl._service = MagicMock()
        ctrl.clear_conversation()
        ctrl._service.clear.assert_called_once()

    def test_clear_conversation_no_service(self, ctrl):
        ctrl._service = None
        ctrl.clear_conversation()

    def test_is_pending_property(self, ctrl):
        ctrl._pending = True
        assert ctrl.is_pending is True
        ctrl._pending = False
        assert ctrl.is_pending is False

    def test_confirm_action_calls_do_confirm(self, ctrl):
        ctrl._worker_mgr = None
        ctrl._service = MagicMock()
        ctrl._service.confirm_action.return_value = {"reply": "done"}
        ctrl._pending = False
        with patch("ui.controllers.ai_assistant_controller.QTimer") as mock_timer:
            mock_timer.singleShot.side_effect = lambda _t, fn: fn()
            ctrl.confirm_action("test_id")
            assert ctrl._pending is False

    def test_cancel_action_calls_service(self, ctrl):
        ctrl._service = MagicMock()
        ctrl._service.cancel_action.return_value = {"reply": "cancelled"}
        results = []
        ctrl.response_received.connect(lambda r: results.append(r))
        ctrl.cancel_action("test_id")
        ctrl._service.cancel_action.assert_called_with("test_id")
        assert len(results) == 1
