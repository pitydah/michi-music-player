"""P0 — pre-execution confirmation flow in MichiAIEngine.

Canonical flow: detect intent → resolve tool → validate args → evaluate risk
→ build plan → request confirmation → execute after accept → record result.

Destructive / confirmation-required tools must NEVER execute inside
process_message(); execution only happens via confirm_plan().
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.ai_engine import MichiAIEngine
from core.ai.intent_router import IntentResult
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


def _make_router(intent_id: str, entities: dict | None = None):
    router = MagicMock()
    router.detect.side_effect = lambda text, context=None: IntentResult(
        intent_id=intent_id,
        confidence=0.9,
        entities=entities or {},
        needs_llm=False,
        raw_text=text,
    )
    return router


def _registry_with(tool_name: str, handler) -> ToolRegistryV2:
    registry = ToolRegistryV2()
    defn = next(d for d in BUILTIN_TOOL_DEFINITIONS if d.name == tool_name)
    registry.register(defn.with_handler(handler))
    return registry


class TestDestructiveNeverExecutesBeforeConfirmation:
    def test_delete_playlist_builds_plan_without_executing(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-42"}),
        )
        result = engine.process_message("borra la playlist Favoritos")

        assert result["ok"] is True
        assert result["requires_confirmation"] is True
        assert result["plan_id"]
        assert result["plan"]["tool"] == "delete_playlist"
        assert result["plan"]["destructive"] is True
        assert result["tool_result"] is None
        handler.assert_not_called()

    def test_risk_is_evaluated_before_execution(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        result = engine.process_message("borra la playlist X")
        assert result["risk_level"] == "moderate"

    def test_pending_plan_is_queryable(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        result = engine.process_message("borra la playlist X")
        pending = engine.get_pending_plan(result["plan_id"])
        assert pending is not None
        assert pending["status"] == "pending"
        assert engine.pending_plans[0]["plan_id"] == result["plan_id"]


class TestExecuteAfterAccept:
    def test_confirm_plan_executes_tool_and_records_result(self):
        handler = MagicMock(return_value={"ok": True, "deleted": 1})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-42"}),
        )
        plan_id = engine.process_message("borra la playlist Favoritos")["plan_id"]

        result = engine.confirm_plan(plan_id)

        assert result["ok"] is True
        assert result["plan_id"] == plan_id
        handler.assert_called_once()
        history = engine.plan_history
        assert len(history) == 1
        assert history[0]["status"] == "executed"
        assert history[0]["result"]["ok"] is True

    def test_confirm_plan_removes_plan_from_pending(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        plan_id = engine.process_message("borra la playlist X")["plan_id"]
        engine.confirm_plan(plan_id)
        assert engine.get_pending_plan(plan_id) is None
        assert engine.pending_plans == []

    def test_confirm_plan_unknown_id_fails(self):
        engine = MichiAIEngine(intent_router=_make_router("greeting"))
        result = engine.confirm_plan("plan-does-not-exist")
        assert result["ok"] is False
        assert result["error"] == "PLAN_NOT_FOUND"

    def test_confirm_plan_tool_failure_is_recorded(self):
        handler = MagicMock(return_value={"ok": False, "error": "boom"})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        plan_id = engine.process_message("borra la playlist X")["plan_id"]
        result = engine.confirm_plan(plan_id)
        assert result["ok"] is False
        assert engine.plan_history[0]["status"] == "failed"


class TestRejectAndCancel:
    def test_reject_plan_never_executes(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        plan_id = engine.process_message("borra la playlist X")["plan_id"]

        result = engine.reject_plan(plan_id)

        assert result["ok"] is True
        assert result["status"] == "rejected"
        handler.assert_not_called()
        assert engine.plan_history[0]["status"] == "rejected"

    def test_cancel_plan_never_executes(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {"playlist_id": "pl-1"}),
        )
        plan_id = engine.process_message("borra la playlist X")["plan_id"]

        result = engine.cancel_plan(plan_id)

        assert result["ok"] is True
        assert result["status"] == "cancelled"
        handler.assert_not_called()
        assert engine.plan_history[0]["status"] == "cancelled"

    def test_reject_unknown_plan_fails(self):
        engine = MichiAIEngine(intent_router=_make_router("greeting"))
        assert engine.reject_plan("nope")["error"] == "PLAN_NOT_FOUND"
        assert engine.cancel_plan("nope")["error"] == "PLAN_NOT_FOUND"


class TestSafeToolsExecuteImmediately:
    def test_safe_tool_runs_without_plan(self):
        handler = MagicMock(return_value={"ok": True, "results": []})
        engine = MichiAIEngine(
            tool_registry=_registry_with("search_library", handler),
            intent_router=_make_router("search_library", {"query": "jazz"}),
        )
        result = engine.process_message("busca jazz")

        assert result["requires_confirmation"] is False
        assert "plan_id" not in result
        handler.assert_called_once()
        assert engine.pending_plans == []

    def test_real_router_playback_intent_has_no_confirmation(self):
        engine = MichiAIEngine()
        result = engine.process_message("reproduce algo de rock")
        assert result["intent"] == "playback_play"
        assert result["requires_confirmation"] is False

    def test_real_router_diagnosis_intent_has_no_confirmation(self):
        engine = MichiAIEngine()
        result = engine.process_message("diagnostica el sistema")
        assert result["intent"] == "diagnosis"
        assert result["requires_confirmation"] is False


class TestArgValidationBeforePlanning:
    def test_invalid_args_fail_fast_without_executing(self):
        handler = MagicMock(return_value={"ok": True})
        engine = MichiAIEngine(
            tool_registry=_registry_with("delete_playlist", handler),
            intent_router=_make_router("delete_playlist", {}),
        )
        defn = next(d for d in BUILTIN_TOOL_DEFINITIONS if d.name == "delete_playlist")
        if not defn.input_schema.get("required"):
            pytest.skip("delete_playlist has no required args to violate")
        result = engine.process_message("borra la playlist")

        assert result["ok"] is False
        assert result["tool_result"]["code"] == "INVALID_ARGUMENTS"
        handler.assert_not_called()
        assert engine.pending_plans == []
