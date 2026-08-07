from __future__ import annotations

import logging
from typing import Any

from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

from core.ai.backends.base import LocalModelBackend
from core.ai.backend_selector import BackendSelector
from core.ai.intent_router import IntentRouter
from core.ai.privacy_guard import PrivacyGuard
from core.ai.risk_policy import RiskPolicy
from core.assistant_runtime import AssistantRuntime

logger = logging.getLogger("michi.ai_engine")


class MichiAIEngine:
    """Thin facade over the single governed ``AssistantRuntime`` (F9).

    The productive composition injects the runtime; the engine then only
    delegates (process_message, plan lifecycle, backend selection, tool
    registry). When constructed without a runtime (tests / standalone use)
    the engine composes one from its injected parts — there is NO duplicate
    intent/risk/pending-plan/confirmation/execution pipeline here.
    """

    def __init__(
        self,
        tool_registry: ToolRegistryV2 | None = None,
        intent_router: IntentRouter | None = None,
        risk_policy: RiskPolicy | None = None,
        privacy_guard: PrivacyGuard | None = None,
        backend_selector: BackendSelector | None = None,
        runtime: AssistantRuntime | None = None,
    ) -> None:
        if runtime is not None:
            self._runtime = runtime
        else:
            # Standalone instantiation (tests): compose the runtime from the
            # injected parts. All subsystem DEFAULTS live in the runtime —
            # the engine never constructs a registry/planner/executor itself.
            self._runtime = AssistantRuntime(
                tool_registry=tool_registry,
                intent_router=intent_router,
                risk_policy=risk_policy,
                privacy_guard=privacy_guard,
                backend_selector=backend_selector,
            )

    @property
    def runtime(self) -> AssistantRuntime:
        return self._runtime

    @property
    def active_backend(self) -> LocalModelBackend:
        return self._runtime.backend_selector.active

    def set_active_backend(self, name: str) -> None:
        self._runtime.backend_selector.set_active(name)

    @property
    def backend_selector(self) -> BackendSelector:
        return self._runtime.backend_selector

    @property
    def tool_registry(self) -> ToolRegistryV2:
        return self._runtime.tool_registry

    def process_message(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Canonical flow delegated to the runtime: intent → plan → confirm →
        execute through the runtime's planner/executor/confirmation policy.

        A tool whose definition requires confirmation (or whose risk level is
        MODERATE/CRITICAL) is NEVER executed inside this method. It returns a
        pending plan instead; execution only happens via confirm_plan().
        """
        return self._runtime.process_message(text, context)

    # ── Plan lifecycle (delegated) ───────────────────────────────────────

    def get_pending_plan(self, plan_id: str) -> dict[str, Any] | None:
        return self._runtime.get_pending_plan(plan_id)

    @property
    def pending_plans(self) -> list[dict[str, Any]]:
        return self._runtime.pending_plans

    @property
    def plan_history(self) -> list[dict[str, Any]]:
        return self._runtime.plan_history

    def confirm_plan(self, plan_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._runtime.confirm_plan(plan_id, context)

    def reject_plan(self, plan_id: str) -> dict[str, Any]:
        return self._runtime.reject_plan(plan_id)

    def cancel_plan(self, plan_id: str) -> dict[str, Any]:
        return self._runtime.cancel_plan(plan_id)

    def cancel(self) -> None:
        self._runtime.cancel()

    def get_suggestions(self, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
        return self._runtime.get_suggestions(context)

    # ── Mapping accessors (delegated; used by the tool-mapping tests) ─────

    def _intent_to_tool(self, intent_id: str) -> str | None:
        """Delegate to the runtime's intent→tool mapping."""
        return self._runtime._intent_to_tool(intent_id)

    def _tool_arguments(self, tool_name: str, intent: Any) -> dict[str, Any]:
        """Delegate to the runtime's entity→argument normalization."""
        return self._runtime._tool_arguments(tool_name, intent)
