from __future__ import annotations

from michi_ai.v2.core.models import (
    ActionPlan, AssistantResponseType, ErrorCode, PlanExecutionResult, PlanState, PlanStep,
)
from michi_ai.v2.core.response_composer import ResponseComposer


class TestResponseComposer:
    def setup_method(self):
        self.composer = ResponseComposer()

    def test_answer(self):
        response = self.composer.compose_answer("Hello world")
        assert response.type == AssistantResponseType.ANSWER
        assert response.message == "Hello world"

    def test_clarification(self):
        response = self.composer.compose_clarification("What do you mean?")
        assert response.type == AssistantResponseType.CLARIFICATION
        assert "What" in response.message

    def test_plan_preview(self):
        step = PlanStep(step_id="s1", tool="play_track")
        plan = ActionPlan(plan_id="p1", session_id="s1", title="Test", steps=(step,))
        response = self.composer.compose_plan_preview(plan)
        assert response.type == AssistantResponseType.PLAN_PREVIEW
        assert response.plan is not None

    def test_confirmation_request(self):
        plan = ActionPlan(plan_id="p1", session_id="s1", title="Delete")
        response = self.composer.compose_confirmation_request(
            plan, summary="Delete everything?",
            risks=("data loss",),
        )
        assert response.type == AssistantResponseType.CONFIRMATION_REQUEST

    def test_execution_progress(self):
        response = self.composer.compose_execution_progress("p1", 1, 3, "RUNNING")
        assert response.type == AssistantResponseType.EXECUTION_PROGRESS
        assert response.progress["current"] == 1
        assert response.progress["total"] == 3

    def test_execution_result_success(self):
        result = PlanExecutionResult(
            ok=True, state=PlanState.SUCCEEDED, plan_id="p1",
            code=ErrorCode.OK, duration_ms=150.0,
        )
        response = self.composer.compose_execution_result(result)
        assert response.type == AssistantResponseType.EXECUTION_RESULT

    def test_execution_result_failure(self):
        result = PlanExecutionResult(
            ok=False, state=PlanState.FAILED, plan_id="p1",
            code=ErrorCode.TOOL_FAILED, error="Tool crashed",
        )
        response = self.composer.compose_execution_result(result)
        assert response.type == AssistantResponseType.ERROR

    def test_error(self):
        response = self.composer.compose_error("Something broke")
        assert response.type == AssistantResponseType.ERROR
        assert "Something" in response.message

    def test_suggestion(self):
        response = self.composer.compose_suggestion(
            "Try this", "You might like X",
        )
        assert response.type == AssistantResponseType.SUGGESTION
