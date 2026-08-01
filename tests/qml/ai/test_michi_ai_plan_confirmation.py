from __future__ import annotations

"""P0 — MichiAIBridge pre-execution confirmation slots.

confirmPlan / rejectPlan / cancelPlan drive the engine plan lifecycle.
Destructive operations never execute before confirmPlan is called.
"""

from unittest.mock import MagicMock

import pytest

from core.ai_engine import MichiAIEngine
from core.ai.intent_router import IntentResult
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


def _make_engine(handler: MagicMock) -> MichiAIEngine:
    router = MagicMock()
    router.detect.side_effect = lambda text, context=None: IntentResult(
        intent_id="delete_playlist",
        confidence=0.9,
        entities={"playlist_id": "pl-42"},
        needs_llm=False,
        raw_text=text,
    )
    registry = ToolRegistryV2()
    defn = next(d for d in BUILTIN_TOOL_DEFINITIONS if d.name == "delete_playlist")
    registry.register(defn.with_handler(handler))
    return MichiAIEngine(tool_registry=registry, intent_router=router)


@pytest.fixture
def handler():
    return MagicMock(return_value={"ok": True, "deleted": 1})


@pytest.fixture
def bridge(handler):
    return MichiAIBridge(michi_ai_service=_make_engine(handler))


class TestConfirmationFlow:
    def test_send_message_plans_without_executing(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        handler.assert_not_called()
        plan = bridge.currentPlan
        assert plan["requires_confirmation"] is True
        assert plan["plan_id"]
        assert plan["tool"] == "delete_playlist"
        assert plan["destructive"] is True

    def test_confirm_plan_executes(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        plan_id = bridge.currentPlan["plan_id"]

        result = bridge.confirmPlan(plan_id)

        assert result["ok"] is True
        handler.assert_called_once()
        assert bridge.status == "SUCCEEDED"
        assert bridge.currentPlan == {}
        assert bridge._pending_action is None
        assert bridge._chat_history[-1]["role"] == "assistant"

    def test_confirm_plan_execution_failure_sets_failed(self, bridge, handler):
        handler.return_value = {"ok": False, "error": "db locked"}
        bridge.sendMessage("borra la playlist Favoritos")
        result = bridge.confirmPlan(bridge.currentPlan["plan_id"])
        assert result["ok"] is False
        assert bridge.status == "FAILED"
        assert bridge.lastError != ""

    def test_reject_plan_never_executes(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        plan_id = bridge.currentPlan["plan_id"]

        result = bridge.rejectPlan(plan_id)

        assert result["ok"] is True
        assert result["status"] == "rejected"
        handler.assert_not_called()
        assert bridge.status == "IDLE"
        assert bridge.currentPlan == {}

    def test_cancel_plan_never_executes(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        plan_id = bridge.currentPlan["plan_id"]

        result = bridge.cancelPlan(plan_id)

        assert result["ok"] is True
        assert result["status"] == "cancelled"
        handler.assert_not_called()
        assert bridge.status == "CANCELLED"

    def test_cancel_clears_engine_pending_plan(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        engine = bridge._ai_engine
        plan_id = bridge.currentPlan["plan_id"]

        bridge.cancel()

        assert bridge.status == "CANCELLED"
        assert engine.get_pending_plan(plan_id) is None
        handler.assert_not_called()

    def test_textual_confirmation_executes_plan(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        bridge.sendMessage("sí")
        handler.assert_called_once()
        assert bridge.status == "SUCCEEDED"

    def test_textual_rejection_never_executes(self, bridge, handler):
        bridge.sendMessage("borra la playlist Favoritos")
        bridge.sendMessage("no")
        handler.assert_not_called()
        assert bridge.status == "IDLE"


class TestConfirmationSlotsWithoutEngine:
    def test_confirm_plan_no_engine(self):
        bridge = MichiAIBridge(michi_ai_service=None)
        result = bridge.confirmPlan("plan-x")
        assert result["ok"] is False
        assert result["error"] == "NO_AI_SERVICE"

    def test_reject_plan_no_engine(self):
        bridge = MichiAIBridge(michi_ai_service=None)
        assert bridge.rejectPlan("plan-x")["error"] == "NO_AI_SERVICE"

    def test_cancel_plan_no_engine(self):
        bridge = MichiAIBridge(michi_ai_service=None)
        assert bridge.cancelPlan("plan-x")["error"] == "NO_AI_SERVICE"


class TestSlotsAreExposedToQml:
    @pytest.mark.parametrize("slot", ["confirmPlan", "rejectPlan", "cancelPlan"])
    def test_slot_signature(self, slot):
        bridge = MichiAIBridge()
        meta = bridge.metaObject()
        signatures = [
            bytes(meta.method(i).methodSignature()).decode()
            for i in range(meta.methodCount())
        ]
        assert any(s.startswith(f"{slot}(QString)") for s in signatures), (
            f"{slot} not exposed as a QML slot"
        )


class TestTextFallbackWithoutPendingPlan:
    def test_si_without_pending_plan_goes_to_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True, "response": "Hecho."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("sí")
        engine.process_message.assert_called_once()
        assert bridge.status == "SUCCEEDED"
