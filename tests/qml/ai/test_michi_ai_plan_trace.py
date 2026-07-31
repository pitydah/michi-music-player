from __future__ import annotations

"""Fase 11.3 — AssistantPage exposes real capabilities, plan, and trace."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def ai_service():
    svc = MagicMock()
    svc.process_message.return_value = {"ok": True, "response": "Hecho."}
    svc.get_suggestions.return_value = []
    return svc


@pytest.fixture
def bridge(ai_service):
    return MichiAIBridge(michi_ai_service=ai_service)


class TestCapabilities:
    def test_capabilities_empty_without_engine(self):
        b = MichiAIBridge(michi_ai_service=None)
        assert b.capabilities == []

    def test_capabilities_from_tool_registry(self, ai_service):
        from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
        from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS

        registry = ToolRegistryV2()
        for defn in BUILTIN_TOOL_DEFINITIONS[:10]:
            registry.register(defn)
        ai_service.tool_registry = registry
        b = MichiAIBridge(michi_ai_service=ai_service)
        caps = b.capabilities
        assert len(caps) > 0
        assert all("area" in c and "tool_count" in c for c in caps)
        assert sum(c["tool_count"] for c in caps if c["available"]) >= 10


class TestCurrentPlan:
    def test_plan_empty_initially(self, bridge):
        assert bridge.currentPlan == {}

    def test_plan_set_on_confirmation_required(self, bridge, ai_service):
        ai_service.process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": "delete_playlist", "risk_level": "critical",
        }
        bridge.sendMessage("borra la playlist Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        plan = bridge.currentPlan
        assert plan["requires_confirmation"] is True
        assert plan["intent"] == "delete_playlist"
        assert plan["risk_level"] == "critical"
        assert plan["action"] == "borra la playlist Favoritos"

    def test_plan_cleared_after_result(self, bridge, ai_service):
        ai_service.process_message.return_value = {"ok": True, "response": "done"}
        bridge.sendMessage("reproduce")
        assert bridge.currentPlan == {}

    def test_plan_cleared_on_cancel(self, bridge, ai_service):
        ai_service.process_message.return_value = {
            "ok": False, "requires_confirmation": True, "intent": "delete_playlist",
        }
        bridge.sendMessage("borra playlist")
        assert bridge.currentPlan != {}
        bridge.cancel()
        assert bridge.currentPlan == {}


class TestLastTrace:
    def test_trace_empty_initially(self, bridge):
        assert bridge.lastTrace == {}

    def test_trace_populated_after_message(self, bridge, ai_service):
        ai_service.process_message.return_value = {
            "ok": True, "response": "ok", "intent": "playback_play",
            "backend": "CalicoBackend", "elapsed_ms": 12,
            "risk_level": "safe", "tool_result": {"ok": True},
        }
        bridge.sendMessage("reproduce algo")
        trace = bridge.lastTrace
        assert trace["intent"] == "playback_play"
        assert trace["backend"] == "CalicoBackend"
        assert trace["elapsed_ms"] == 12
        assert trace["tool_ok"] is True

    def test_trace_records_error(self, bridge, ai_service):
        ai_service.process_message.side_effect = RuntimeError("boom")
        bridge.sendMessage("falla")
        assert bridge.lastTrace["error"] == "boom"
