from __future__ import annotations


from michi_ai.v2.core.models import (
    ActionPlan, PlanValidationResult, PlanStep,
)
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class PlanValidator:
    MAX_STEPS = 50
    MAX_DEPTH = 10
    MAX_TIMEOUT = 600

    def __init__(self, tool_registry: ToolRegistryV2, capability_resolver: CapabilityResolver | None = None) -> None:
        self._tool_registry = tool_registry
        self._capability_resolver = capability_resolver or tool_registry.capability_resolver

    def validate(self, plan: ActionPlan) -> PlanValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not plan.plan_id:
            errors.append("Plan missing plan_id")

        if not plan.session_id:
            warnings.append("Plan missing session_id")

        if not plan.steps:
            warnings.append("Plan has no steps")
            return PlanValidationResult(
                status="VALID_WITH_WARNINGS" if not errors else "INVALID",
                errors=tuple(errors), warnings=tuple(warnings),
            )

        if len(plan.steps) > self.MAX_STEPS:
            errors.append(f"Plan exceeds max steps ({len(plan.steps)} > {self.MAX_STEPS})")

        step_ids = set()
        for step in plan.steps:
            step_id_error = self._validate_step(step, plan)
            if step_id_error:
                errors.append(step_id_error)
            if step.step_id in step_ids:
                errors.append(f"Duplicate step_id: {step.step_id}")
            step_ids.add(step.step_id)

        cycle_error = self._detect_cycle(plan.steps)
        if cycle_error:
            errors.append(cycle_error)

        cap_error = self._validate_capabilities(plan)
        if cap_error:
            errors.append(cap_error)

        if plan.expires_at:
            import datetime
            try:
                expires = datetime.datetime.fromisoformat(plan.expires_at)
                if expires < datetime.datetime.now(datetime.timezone.utc):
                    errors.append("Plan has already expired")
            except (ValueError, TypeError):
                warnings.append("Cannot parse expires_at")

        if errors:
            return PlanValidationResult(status="INVALID", errors=tuple(errors), warnings=tuple(warnings))
        if warnings:
            return PlanValidationResult(status="VALID_WITH_WARNINGS", errors=(), warnings=tuple(warnings))
        return PlanValidationResult(status="VALID", errors=(), warnings=())

    def _validate_step(self, step: PlanStep, plan: ActionPlan) -> str | None:
        if not step.step_id:
            return "Step missing step_id"

        if step.timeout > self.MAX_TIMEOUT:
            return f"Step '{step.step_id}' timeout {step.timeout}s exceeds max {self.MAX_TIMEOUT}s"

        if step.tool:
            tool_defn = self._tool_registry.get(step.tool)
            if tool_defn is None:
                return f"Step '{step.step_id}': tool '{step.tool}' not found"

        for dep in step.depends_on:
            if dep not in {s.step_id for s in plan.steps}:
                return f"Step '{step.step_id}' depends on unknown step '{dep}'"

        return None

    def _detect_cycle(self, steps: list[PlanStep]) -> str | None:
        dep_map: dict[str, list[str]] = {}
        for step in steps:
            dep_map[step.step_id] = list(step.depends_on)

        visited: set[str] = set()
        path: set[str] = set()

        def _dfs(node: str) -> bool:
            if node in path:
                return True
            if node in visited:
                return False
            visited.add(node)
            path.add(node)
            for dep in dep_map.get(node, []):
                if _dfs(dep):
                    return True
            path.remove(node)
            return False

        for step in steps:
            if _dfs(step.step_id):
                return f"Circular dependency detected involving step '{step.step_id}'"
        return None

    def _validate_capabilities(self, plan: ActionPlan) -> str | None:
        needed: set[str] = set()
        for step in plan.steps:
            if step.tool:
                defn = self._tool_registry.get(step.tool)
                if defn:
                    needed.update(defn.capabilities)

        if not needed:
            return None

        unavailable = [n for n in needed if not self._capability_resolver.all_available(n)]
        if unavailable:
            return f"Unavailable capabilities: {', '.join(unavailable)}"
        return None
