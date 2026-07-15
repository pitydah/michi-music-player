from __future__ import annotations

import time

from michi_ai.v2.core.models import ConfirmationMode, ErrorCode, PlanStep
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2


class TestConfirmationPolicyV2:
    def test_none_mode_never_requires(self):
        policy = ConfirmationPolicyV2(mode=ConfirmationMode.NONE)
        step = PlanStep(step_id="s1", tool="delete")
        assert policy.requires_confirmation(step) is False

    def test_always_mode_always_requires(self):
        policy = ConfirmationPolicyV2(mode=ConfirmationMode.EXPLICIT)
        step = PlanStep(step_id="s1", tool="play_track")
        assert policy.requires_confirmation(step) is True

    def test_destructive_action_requires(self):
        from michi_ai.v2.core.models import ToolDefinition, PermissionLevel
        policy = ConfirmationPolicyV2(mode=ConfirmationMode.DESTRUCTIVE)
        step = PlanStep(step_id="s1", tool="delete_playlist")
        tool_defn = ToolDefinition(name="delete_playlist", description="", destructive=True, permission=PermissionLevel.DESTRUCTIVE)
        assert policy.requires_confirmation(step, tool_defn=tool_defn) is True

    def test_read_only_action_no_confirmation(self):
        from michi_ai.v2.core.models import ToolDefinition, PermissionLevel
        policy = ConfirmationPolicyV2(mode=ConfirmationMode.DESTRUCTIVE)
        step = PlanStep(step_id="s1", tool="search_library")
        tool_defn = ToolDefinition(name="search_library", description="", permission=PermissionLevel.READ_ONLY)
        assert policy.requires_confirmation(step, tool_defn=tool_defn) is False

    def test_issue_creates_request(self):
        policy = ConfirmationPolicyV2()
        request = policy.issue(
            plan_id="p1", summary="Delete tracks",
            risks=("data loss",),
        )
        assert request.confirmation_id != ""
        assert request.plan_id == "p1"
        assert "data loss" in request.risks

    def test_validate_valid_confirmation(self):
        policy = ConfirmationPolicyV2()
        request = policy.issue(plan_id="p1", summary="test")
        result = policy.validate(request.confirmation_id, "p1")
        assert result.ok is True

    def test_validate_expired_confirmation(self):
        policy = ConfirmationPolicyV2(ttl_seconds=0)
        request = policy.issue(plan_id="p1", summary="test")
        time.sleep(0.01)
        result = policy.validate(request.confirmation_id, "p1")
        assert result.ok is False
        assert result.code == ErrorCode.CONFIRMATION_EXPIRED

    def test_validate_wrong_plan(self):
        policy = ConfirmationPolicyV2()
        request = policy.issue(plan_id="p1", summary="test")
        result = policy.validate(request.confirmation_id, "p2")
        assert result.ok is False

    def test_single_use_consumption(self):
        policy = ConfirmationPolicyV2()
        request = policy.issue(plan_id="p1", summary="test")
        first = policy.validate(request.confirmation_id, "p1")
        assert first.ok is True
        second = policy.validate(request.confirmation_id, "p1")
        assert second.ok is False
        assert second.code == ErrorCode.CONFIRMATION_EXPIRED

    def test_clean_expired(self):
        policy = ConfirmationPolicyV2(ttl_seconds=0)
        policy.issue(plan_id="p1", summary="test")
        time.sleep(0.01)
        cleaned = policy.clean_expired()
        assert cleaned > 0

    def test_pending_count(self):
        policy = ConfirmationPolicyV2()
        r1 = policy.issue(plan_id="p1", summary="1")
        policy.issue(plan_id="p2", summary="2")
        assert policy.pending_count() == 2
        policy.validate(r1.confirmation_id, "p1")
        assert policy.pending_count() == 1

    def test_clear(self):
        policy = ConfirmationPolicyV2()
        policy.issue(plan_id="p1", summary="test")
        policy.clear()
        assert policy.pending_count() == 0

    def test_plan_requires_confirmation(self):
        policy = ConfirmationPolicyV2(mode=ConfirmationMode.SOFT)
        step = PlanStep(step_id="s1", tool="play_track")
        assert policy.requires_confirmation(step, plan_requires=True) is True
