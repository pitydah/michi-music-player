from __future__ import annotations

from michi_ai.v2.core.models import (
    ActionPlan, ConfirmationRequest, ConversationTurn,
    ErrorCode, OperationResult, ParsedIntent, PlanStep, PlanValidationResult,
    ToolDefinition, ToolExecutionResult,
)


class TestOperationResult:
    def test_success_creates_ok_result(self):
        result = OperationResult.success(data={"key": "value"}, message="done")
        assert result.ok is True
        assert result.code == ErrorCode.OK
        assert result.data == {"key": "value"}
        assert result.message == "done"
        assert result.correlation_id != ""

    def test_failure_creates_error_result(self):
        result = OperationResult.failure(ErrorCode.TOOL_NOT_FOUND, "Tool missing")
        assert result.ok is False
        assert result.code == ErrorCode.TOOL_NOT_FOUND
        assert result.message == "Tool missing"
        assert result.retryable is False

    def test_confirmation_creates_confirmation_result(self):
        result = OperationResult.confirmation("Are you sure?")
        assert result.ok is False
        assert result.code == ErrorCode.CONFIRMATION_REQUIRED
        assert result.requires_confirmation is True

    def test_with_data_preserves_fields(self):
        r1 = OperationResult.success(data=1)
        r2 = r1.with_data(2)
        assert r2.data == 2
        assert r2.ok is True
        assert r2.correlation_id == r1.correlation_id

    def test_with_warning_appends_warning(self):
        r = OperationResult.success().with_warning("disk full")
        assert "disk full" in r.warnings


class TestToolDefinition:
    def test_minimal_definition(self):
        t = ToolDefinition(name="test_tool", description="A test")
        assert t.name == "test_tool"
        assert t.version == "1.0.0"
        assert t.timeout_seconds == 30
        assert t.handler is None

    def test_full_definition(self):
        def handler(**kwargs):
            return {"ok": True}
        t = ToolDefinition(
            name="full_tool", description="Full", version="2.0",
            input_schema={"required": ["arg1"]},
            permission="DESTRUCTIVE",
            destructive=True, cancellable=True, timeout_seconds=60,
            handler=handler,
        )
        assert t.destructive is True
        assert t.cancellable is True


class TestActionPlan:
    def test_empty_plan(self):
        plan = ActionPlan(plan_id="p1", session_id="s1")
        assert plan.plan_id == "p1"
        assert plan.steps == ()

    def test_plan_with_steps(self):
        step = PlanStep(step_id="s0", tool="play_track", arguments={"track": "test"})
        plan = ActionPlan(
            plan_id="p1", session_id="s1",
            title="Test", steps=(step,),
            risks=("risk1",),
        )
        assert len(plan.steps) == 1
        assert plan.steps[0].tool == "play_track"
        assert "risk1" in plan.risks


class TestParsedIntent:
    def test_minimal_intent(self):
        intent = ParsedIntent(intent_id="play_track", confidence=0.9, source="rules")
        assert intent.intent_id == "play_track"
        assert intent.confidence == 0.9
        assert intent.entities == {}

    def test_with_entities(self):
        intent = ParsedIntent(
            intent_id="play_album", confidence=0.85, source="rules",
            entities={"artist": "Radiohead", "album": "OK Computer"},
        )
        assert intent.entities["artist"] == "Radiohead"

    def test_clarification(self):
        intent = ParsedIntent(
            intent_id="unknown", confidence=0.3, source="fallback",
            requires_clarification=True,
            clarification_question="Which one?",
        )
        assert intent.requires_clarification is True


class TestToolExecutionResult:
    def test_success_result(self):
        r = ToolExecutionResult(ok=True, tool_name="test", data={"result": 42})
        assert r.ok is True
        assert r.data == {"result": 42}

    def test_failure_result(self):
        r = ToolExecutionResult(ok=False, tool_name="test", error="Failed", code=ErrorCode.TOOL_FAILED)
        assert r.ok is False
        assert r.code == ErrorCode.TOOL_FAILED


class TestConversationTurn:
    def test_user_turn(self):
        t = ConversationTurn(role="user", content="hello")
        assert t.role == "user"
        assert t.content == "hello"

    def test_assistant_turn_with_tool(self):
        t = ConversationTurn(
            role="assistant", content="Done",
            tool_name="play_track", tool_result={"ok": True},
        )
        assert t.tool_name == "play_track"


class TestConfirmationRequest:
    def test_minimal(self):
        c = ConfirmationRequest(confirmation_id="c1", plan_id="p1")
        assert c.confirmation_id == "c1"
        assert c.single_use is True


class TestPlanValidationResult:
    def test_valid(self):
        r = PlanValidationResult(status="VALID")
        assert r.status == "VALID"

    def test_invalid(self):
        r = PlanValidationResult(status="INVALID", errors=("err1",))
        assert r.errors == ("err1",)
