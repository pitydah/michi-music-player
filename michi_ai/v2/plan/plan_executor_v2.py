from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from michi_ai.v2.core.cancellation import CancellationToken, CancellationSource
from michi_ai.v2.core.models import (
    ActionPlan, ErrorCode, PlanExecution, PlanExecutionResult,
    PlanState, ToolExecutionResult, PlanStep,
)
from michi_ai.v2.core.gateways import JobGateway
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

logger = logging.getLogger(__name__)


class PlanExecutorV2:
    def __init__(self, tool_registry: ToolRegistryV2, job_gateway: JobGateway | None = None) -> None:
        self._tool_registry = tool_registry
        self._job_gateway = job_gateway
        self._executions: dict[str, PlanExecution] = {}
        self._cancellation_sources: dict[str, CancellationSource] = {}
        self._on_progress: list[Callable[[str, PlanState, int, int], None]] = []
        self._on_complete: list[Callable[[PlanExecution], None]] = []

    def on_progress(self, callback: Callable[[str, PlanState, int, int], None]) -> None:
        self._on_progress.append(callback)

    def on_complete(self, callback: Callable[[PlanExecution], None]) -> None:
        self._on_complete.append(callback)

    def execute(self, plan: ActionPlan, cancellation_token: CancellationToken | None = None) -> PlanExecutionResult:
        execution = PlanExecution(
            plan=plan,
            state=PlanState.CREATED,
            started_at=datetime.now(timezone.utc).isoformat(),
            correlation_id=uuid.uuid4().hex[:12],
        )
        self._executions[plan.plan_id] = execution
        canceller = CancellationSource()
        self._cancellation_sources[plan.plan_id] = canceller
        token = cancellation_token or canceller.token
        start = time.monotonic()

        try:
            execution.state = PlanState.VALIDATING
            self._notify_progress(plan.plan_id, execution.state, 0, len(plan.steps))

            if plan.requires_confirmation:
                execution.state = PlanState.AWAITING_CONFIRMATION
                self._notify_progress(plan.plan_id, execution.state, 0, len(plan.steps))
                return PlanExecutionResult(
                    ok=False, state=PlanState.AWAITING_CONFIRMATION,
                    plan_id=plan.plan_id,
                    code=ErrorCode.CONFIRMATION_REQUIRED,
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            execution.state = PlanState.QUEUED
            self._notify_progress(plan.plan_id, execution.state, 0, len(plan.steps))

            execution.state = PlanState.RUNNING
            completed_steps: list[ToolExecutionResult] = []

            step_order = self._resolve_order(plan.steps)
            for step_index in step_order:
                step = plan.steps[step_index]

                if token.cancelled:
                    execution.state = PlanState.CANCELLED
                    execution.error = token.reason
                    duration = (time.monotonic() - start) * 1000
                    result = PlanExecutionResult(
                        ok=False, state=PlanState.CANCELLED, plan_id=plan.plan_id,
                        step_results=tuple(completed_steps),
                        code=ErrorCode.PLAN_CANCELLED, duration_ms=duration,
                        error=token.reason,
                    )
                    self._notify_complete(execution)
                    return result

                token.check()
                self._notify_progress(plan.plan_id, execution.state, len(completed_steps), len(plan.steps))

                step_result = self._execute_step(step, token, execution.correlation_id)
                completed_steps.append(step_result)
                execution.step_results.append(step_result)
                execution.current_step_index = step_index

                if not step_result.ok:
                    logger.warning("Step '%s' failed: %s", step.step_id, step_result.error)
                    if step.on_failure == "STOP":
                        execution.state = PlanState.FAILED
                        execution.error = step_result.error
                        duration = (time.monotonic() - start) * 1000
                        return PlanExecutionResult(
                            ok=False, state=PlanState.FAILED, plan_id=plan.plan_id,
                            step_results=tuple(completed_steps),
                            code=ErrorCode.PLAN_STEP_FAILED,
                            duration_ms=duration, error=step_result.error,
                        )
                    elif step.on_failure == "ROLLBACK":
                        return self._rollback(execution, completed_steps, start)
                    elif step.on_failure == "CONTINUE" or step.on_failure == "MARK_PARTIAL":
                        execution.state = PlanState.PARTIAL_SUCCESS
                    else:
                        execution.state = PlanState.FAILED
                        execution.error = step_result.error
                        duration = (time.monotonic() - start) * 1000
                        return PlanExecutionResult(
                            ok=False, state=PlanState.FAILED, plan_id=plan.plan_id,
                            step_results=tuple(completed_steps),
                            code=ErrorCode.PLAN_STEP_FAILED,
                            duration_ms=duration, error=step_result.error,
                        )

            execution.state = PlanState.SUCCEEDED
            duration = (time.monotonic() - start) * 1000
            result = PlanExecutionResult(
                ok=True, state=PlanState.SUCCEEDED, plan_id=plan.plan_id,
                step_results=tuple(completed_steps),
                code=ErrorCode.OK, duration_ms=duration,
            )
            self._notify_complete(execution)
            return result

        except Exception as e:
            execution.state = PlanState.INTERRUPTED
            execution.error = str(e)
            duration = (time.monotonic() - start) * 1000
            return PlanExecutionResult(
                ok=False, state=PlanState.INTERRUPTED, plan_id=plan.plan_id,
                code=ErrorCode.INTERNAL_ERROR, duration_ms=duration, error=str(e),
            )
        finally:
            self._cancellation_sources.pop(plan.plan_id, None)

    def _execute_step(
        self, step: PlanStep, token: CancellationToken, correlation_id: str,
    ) -> ToolExecutionResult:
        if not step.tool:
            return ToolExecutionResult(ok=True, tool_name="", correlation_id=correlation_id)

        if token.cancelled:
            return ToolExecutionResult(
                ok=False, tool_name=step.tool, error="Cancelled",
                code=ErrorCode.TOOL_CANCELLED, correlation_id=correlation_id,
            )

        return self._tool_registry.execute(
            name=step.tool,
            arguments=step.arguments,
            cancellation_token=token,
            correlation_id=correlation_id,
        )

    def _resolve_order(self, steps: list[PlanStep]) -> list[int]:
        step_ids = [s.step_id for s in steps]
        dep_map: dict[str, set[str]] = {}
        for s in steps:
            dep_map[s.step_id] = set(s.depends_on)

        ordered: list[int] = []
        remaining = set(range(len(steps)))

        while remaining:
            batch = []
            for i in remaining:
                step = steps[i]
                deps = dep_map[step.step_id]
                if not deps or all(
                    step_ids.index(d) in ordered for d in deps if d in step_ids
                ):
                    batch.append(i)
            if not batch:
                ordered.extend(remaining)
                break
            ordered.extend(batch)
            remaining -= set(batch)

        return ordered

    def cancel(self, plan_id: str, reason: str = "cancelled by user") -> bool:
        source = self._cancellation_sources.get(plan_id)
        if source is None:
            execution = self._executions.get(plan_id)
            if execution:
                execution.state = PlanState.CANCELLED
                execution.error = reason
                self._notify_complete(execution)
            return False
        source.cancel(reason)
        execution = self._executions.get(plan_id)
        if execution:
            execution.state = PlanState.CANCELLING
        return True

    def get_execution(self, plan_id: str) -> PlanExecution | None:
        return self._executions.get(plan_id)

    def _rollback(self, execution: PlanExecution, completed: list[ToolExecutionResult], start: float) -> PlanExecutionResult:
        execution.state = PlanState.ROLLING_BACK
        rolled_back: list[str] = []
        failed: list[str] = []

        for step_result in reversed(completed):
            step_id = step_result.tool_name
            defn = self._tool_registry.get(step_id)
            rb_tool = defn.rollback_tool if defn and defn.rollback_tool else ""
            compensate_tool = ""
            for step in execution.plan.steps:
                if step.tool == step_id:
                    compensate_tool = step.compensate
                    break
            rollback_target = rb_tool or compensate_tool
            if rollback_target:
                rb_result = self._tool_registry.execute(
                    name=rollback_target,
                    arguments=step_result.data or {},
                )
                if rb_result.ok:
                    rolled_back.append(step_id)
                else:
                    failed.append(step_id)
            else:
                rolled_back.append(step_id)

        execution.state = PlanState.ROLLED_BACK
        duration = (time.monotonic() - start) * 1000
        code = ErrorCode.ROLLBACK_SUCCEEDED if not failed else ErrorCode.ROLLBACK_FAILED
        return PlanExecutionResult(
            ok=not bool(failed), state=PlanState.ROLLED_BACK,
            plan_id=execution.plan.plan_id,
            step_results=tuple(completed),
            code=code, duration_ms=duration,
            error=f"Rolled back: {rolled_back}, failed: {failed}" if failed else "",
        )

    def _notify_progress(self, plan_id: str, state: PlanState, current: int, total: int) -> None:
        for cb in self._on_progress:
            try:
                cb(plan_id, state, current, total)
            except Exception as e:
                logger.debug("Progress callback error: %s", e)

    def _notify_complete(self, execution: PlanExecution) -> None:
        for cb in self._on_complete:
            try:
                cb(execution)
            except Exception as e:
                logger.debug("Complete callback error: %s", e)
