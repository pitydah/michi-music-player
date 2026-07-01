"""Tests for Michi AI — core modules."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from michi_ai.tools.tool_result import ToolResult
from michi_ai.tools.tool_permissions import ToolPermission, permission_requires_confirmation
from michi_ai.tools.tool_registry import ToolRegistry, ToolDef
from michi_ai.context.ai_event_mapper import map_event
from michi_ai.context.ai_context_bridge import MichiAIContextBridge
from michi_ai.context.ai_snapshot_service import MichiAISnapshotService
from michi_ai.context.ai_insight_service import MichiAIInsightService
from michi_ai.planner.action_plan import ActionPlan, PlanStep
from michi_ai.planner.plan_builder import PlanBuilder
from michi_ai.planner.plan_executor import PlanExecutor
from michi_ai.planner.confirmation_policy import requires_confirmation as confirm_policy
from michi_ai.tools.library_tools import get_library_health, search_library, summarize_current_selection
from michi_ai.tools.sync_tools import get_sync_status, list_sync_peers


class TestToolResult:
    def test_ok_default(self):
        r = ToolResult()
        assert r.ok is True
        assert r.code == "OK"

    def test_fail(self):
        r = ToolResult(ok=False, code="ERROR", message="fail")
        assert r.ok is False


class TestToolPermissions:
    def test_read_only_no_confirmation(self):
        assert permission_requires_confirmation(ToolPermission.READ_ONLY) is False

    def test_config_change_requires_confirmation(self):
        assert permission_requires_confirmation(ToolPermission.CONFIG_CHANGE) is True

    def test_destructive_requires_confirmation(self):
        assert permission_requires_confirmation(ToolPermission.DESTRUCTIVE) is True


class TestToolRegistry:
    def test_register_and_list(self):
        reg = ToolRegistry()
        reg.register(ToolDef("test", "Test tool", ToolPermission.READ_ONLY, fn=lambda: ToolResult(ok=True)))
        assert len(reg.list_tools()) == 1

    def test_execute_read_only(self):
        reg = ToolRegistry()
        reg.register(ToolDef("read", "Read only", ToolPermission.READ_ONLY, fn=lambda: ToolResult(ok=True, data={"key": "val"})))
        result = reg.execute("read")
        assert result.ok is True

    def test_execute_blocked_without_confirmation(self):
        reg = ToolRegistry()
        reg.register(ToolDef("write", "Write", ToolPermission.CONFIG_CHANGE, fn=lambda: ToolResult(ok=True)))
        result = reg.execute("write")
        assert result.ok is False
        assert result.requires_confirmation is True

    def test_execute_confirmed(self):
        reg = ToolRegistry()
        reg.register(ToolDef("write", "Write", ToolPermission.CONFIG_CHANGE, fn=lambda: ToolResult(ok=True)))
        result = reg.execute("write", confirmed=True)
        assert result.ok is True

    def test_execute_not_found(self):
        reg = ToolRegistry()
        result = reg.execute("nonexistent")
        assert result.ok is False
        assert result.code == "NOT_FOUND"

    def test_execute_exception_handled(self):
        reg = ToolRegistry()
        def _failing():
            raise RuntimeError("boom")
        reg.register(ToolDef("fail", "Fails", ToolPermission.READ_ONLY, fn=_failing))
        result = reg.execute("fail")
        assert result.ok is False
        assert result.code == "ERROR"


class TestEventMapper:
    def test_known_event(self):
        assert map_event("sync_started") == "Michi Sync iniciado"

    def test_unknown_event_passthrough(self):
        assert map_event("unknown_event") == "unknown_event"


class TestContextBridge:
    def test_record_tool_result(self):
        ctx = MagicMock()
        bridge = MichiAIContextBridge(context_service=ctx)
        bridge.record_tool_result("test_tool", True)
        assert ctx.record_event.called

    def test_connect_sync_manager_none(self):
        bridge = MichiAIContextBridge()
        bridge.connect_sync_manager(None)
        assert True


class TestSnapshotService:
    def test_build_snapshot_no_context(self):
        svc = MichiAISnapshotService()
        snap = svc.build_snapshot()
        assert "route" in snap
        assert "sync" in snap

    def test_build_snapshot_with_context(self):
        ctx = MagicMock()
        ctx.get_assistant_snapshot.return_value = {"route": {"current_section": "test"}, "playback": {}, "library_health": {"track_count": 100}, "recent_events": [], "assistant_capabilities": {}}
        svc = MichiAISnapshotService(context_service=ctx)
        snap = svc.build_snapshot()
        assert snap["route"]["current_section"] == "test"


class TestInsightService:
    def test_empty_library_insight(self):
        svc = MichiAIInsightService()
        snapshot = {"library_health": {"track_count": 0}, "sync": {"active": False}, "selection": {}}
        insights = svc.generate(snapshot)
        assert any(i["id"] == "empty_library" for i in insights)

    def test_missing_metadata_insight(self):
        svc = MichiAIInsightService()
        snapshot = {"library_health": {"track_count": 100, "missing_metadata_count": 5}, "sync": {"active": False}, "selection": {}}
        insights = svc.generate(snapshot)
        assert any(i["id"] == "missing_metadata" for i in insights)

    def test_sync_disabled_insight(self):
        svc = MichiAIInsightService()
        snapshot = {"library_health": {"track_count": 100}, "sync": {"active": False}, "selection": {}}
        insights = svc.generate(snapshot)
        assert any(i["id"] == "sync_disabled" for i in insights)


class TestPlanBuilder:
    def test_create_plan(self):
        pb = PlanBuilder()
        plan = pb.create_plan("prepare_mobile_sync")
        assert plan.title == "Preparar sincronizacion movil"
        assert len(plan.steps) > 0

    def test_unknown_plan_type(self):
        pb = PlanBuilder()
        with pytest.raises(ValueError):
            pb.create_plan("nonexistent")

    def test_list_plan_types(self):
        pb = PlanBuilder()
        types = pb.list_plan_types()
        assert len(types) >= 6


class TestPlanExecutor:
    def test_preview(self):
        reg = ToolRegistry()
        executor = PlanExecutor(reg)
        plan = ActionPlan(plan_id="test", title="Test", description="Desc", steps=[PlanStep(tool="read")])
        preview = executor.preview(plan)
        assert preview["plan_id"] == "test"

    def test_execute_requires_confirmation(self):
        reg = ToolRegistry()
        executor = PlanExecutor(reg)
        plan = ActionPlan(plan_id="test", title="Test", description="Desc")
        result = executor.execute(plan, confirmed=False)
        assert result.ok is False
        assert result.requires_confirmation is True


class TestConfirmationPolicy:
    def test_read_only_no_confirm(self):
        assert confirm_policy(ToolPermission.READ_ONLY) is False

    def test_resource_intensive_confirm(self):
        assert confirm_policy(ToolPermission.RESOURCE_INTENSIVE) is True

    def test_config_change_confirm(self):
        assert confirm_policy(ToolPermission.CONFIG_CHANGE) is True


class TestLibraryTools:
    def test_get_library_health_no_db(self):
        result = get_library_health(db=None)
        assert result.ok is False

    def test_search_library_no_query(self):
        result = search_library(db=MagicMock(), query="")
        assert result.ok is False

    def test_summarize_current_selection(self):
        result = summarize_current_selection(selection={"scope": "track", "track": "Song"})
        assert result.ok is True
        assert result.data["scope"] == "track"


class TestSyncTools:
    def test_get_sync_status_no_manager(self):
        result = get_sync_status(sync_manager=None)
        assert result.ok is True

    def test_list_sync_peers_no_manager(self):
        result = list_sync_peers(sync_manager=None)
        assert result.ok is True
