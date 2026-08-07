"""AssistantRuntime — the single governed composition of the assistant's
internal subsystems (F9, ADR-006).

The productive runtime registers ONE object (``assistant_runtime``) that
contains and governs: intent resolution, capability resolution, context
assembly, plan builder, plan validation, confirmation policy, plan
execution, tool registry, conversation service, trace recorder and backend
selection. ``MichiAIEngine`` is a thin facade over this runtime; there is
exactly ONE planner, ONE executor, ONE capability resolver and ONE tool
registry in the composition (no duplicate pipelines).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from michi_ai.v2.context.context_assembler import ContextAssembler
from michi_ai.v2.conversation.conversation_service import ConversationService
from michi_ai.v2.core.cancellation import CancellationSource
from michi_ai.v2.core.models import (
    AssistantTrace,
    ParsedIntent,
    PlanStep,
    PrivacyLevel,
    ProviderRequest,
)
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
from michi_ai.v2.trace.trace_recorder import TraceRecorder
from michi_ai.tools.tool_result import ToolResult

from core.ai.backend_selector import BackendSelector
from core.ai.backends.base import LocalModelBackend
from core.ai.backends.calico import CalicoBackend
from core.ai.intent_router import IntentResult, IntentRouter
from core.ai.privacy_guard import PrivacyGuard, SanitizedSnapshot
from core.ai.risk_policy import RiskLevel, RiskPolicy

logger = logging.getLogger("michi.assistant_runtime")

_MAX_PLAN_HISTORY = 200


class AssistantRuntime:
    """Single governed composition of every assistant internal subsystem.

    Controlled interfaces (read-only properties): tool_registry,
    capability_resolver, planner, validator, executor, context_assembler,
    conversation_service, confirmation_policy, trace_recorder and
    backend_selector. External layers delegate through them; nothing else
    mutates the runtime's subsystems.
    """

    def __init__(
        self,
        tool_registry: ToolRegistryV2 | None = None,
        capability_resolver: CapabilityResolver | None = None,
        planner: PlanBuilderV2 | None = None,
        validator: PlanValidator | None = None,
        executor: PlanExecutorV2 | None = None,
        context_assembler: ContextAssembler | None = None,
        conversation_service: ConversationService | None = None,
        confirmation_policy: ConfirmationPolicyV2 | None = None,
        trace_recorder: TraceRecorder | None = None,
        backend_selector: BackendSelector | None = None,
        intent_router: IntentRouter | None = None,
        risk_policy: RiskPolicy | None = None,
        privacy_guard: PrivacyGuard | None = None,
        lite_backend: LocalModelBackend | None = None,
        trace_enabled: bool = False,
    ) -> None:
        self._tool_registry = tool_registry or ToolRegistryV2()
        self._capability_resolver = (
            capability_resolver or self._tool_registry.capability_resolver
        )
        self._planner = planner or PlanBuilderV2(
            self._tool_registry, self._capability_resolver
        )
        self._validator = validator or PlanValidator(
            self._tool_registry, self._capability_resolver
        )
        self._executor = executor or PlanExecutorV2(self._tool_registry)
        self._context_assembler = context_assembler or ContextAssembler()
        self._conversation_service = conversation_service or ConversationService()
        self._confirmation_policy = confirmation_policy or ConfirmationPolicyV2()
        self._trace_recorder = trace_recorder
        self._backend_selector = backend_selector or BackendSelector()
        self._intent_router = intent_router or IntentRouter()
        self._risk_policy = risk_policy or RiskPolicy()
        self._privacy_guard = privacy_guard or PrivacyGuard()
        self._lite_backend = lite_backend or CalicoBackend()
        self._trace_enabled = bool(trace_recorder is not None) and trace_enabled
        # Plans awaiting explicit user confirmation. A destructive or
        # confirmation-required tool NEVER runs before confirm_plan() is
        # called with the matching plan_id (runtime confirmation policy).
        self._pending_plans: dict[str, dict[str, Any]] = {}
        self._plan_history: list[dict[str, Any]] = []
        self._cancelled = False

    # ── Controlled interfaces (read-only) ────────────────────────────────

    @property
    def tool_registry(self) -> ToolRegistryV2:
        return self._tool_registry

    @property
    def capability_resolver(self) -> CapabilityResolver:
        return self._capability_resolver

    @property
    def planner(self) -> PlanBuilderV2:
        return self._planner

    @property
    def validator(self) -> PlanValidator:
        return self._validator

    @property
    def executor(self) -> PlanExecutorV2:
        return self._executor

    @property
    def context_assembler(self) -> ContextAssembler:
        return self._context_assembler

    @property
    def conversation_service(self) -> ConversationService:
        return self._conversation_service

    @property
    def confirmation_policy(self) -> ConfirmationPolicyV2:
        return self._confirmation_policy

    @property
    def trace_recorder(self) -> TraceRecorder | None:
        return self._trace_recorder

    @property
    def backend_selector(self) -> BackendSelector:
        return self._backend_selector

    @property
    def intent_router(self) -> IntentRouter:
        return self._intent_router

    @property
    def risk_policy(self) -> RiskPolicy:
        return self._risk_policy

    # ── Public pipeline (engine-compatible dict API) ─────────────────────

    def process_message(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Canonical flow: intent → tool → args → risk → plan → validate →
        confirm → execute, all through the runtime's governed subsystems."""
        self._cancelled = False
        start = time.monotonic()

        try:
            sanitized = self._privacy_guard.sanitize_input(text)
            merged = self._assemble_context(context)
            intent: IntentResult = self._intent_router.detect(sanitized, merged)

            # Resolve tool + normalize args before any execution decision.
            tool_name = self._intent_to_tool(intent.intent_id)
            args: dict[str, Any] = {}
            defn = None
            if tool_name:
                args = self._tool_arguments(tool_name, intent)
                defn = self._tool_registry.get(tool_name)
                if defn is not None:
                    validation_error = self._tool_registry._validate_args(defn, args)
                    if validation_error:
                        elapsed = time.monotonic() - start
                        return {
                            "ok": False,
                            "response": f"Argumentos inválidos: {validation_error}",
                            "intent": intent.intent_id,
                            "confidence": intent.confidence,
                            "needs_llm": intent.needs_llm,
                            "risk_level": RiskLevel.SAFE.value,
                            "requires_confirmation": False,
                            "tool_result": {"ok": False, "code": "INVALID_ARGUMENTS", "message": validation_error, "data": {}},
                            "elapsed_ms": round(elapsed * 1000),
                            "backend": type(self._backend_selector.active).__name__,
                        }

            # Evaluate risk BEFORE execution.
            risk_level = self._risk_policy.get_risk(intent.intent_id)
            needs_confirmation = bool(tool_name) and (
                self._risk_policy.require_confirmation(risk_level)
                or (defn is not None and (defn.requires_confirmation or defn.destructive))
            )

            if tool_name and needs_confirmation:
                plan_entry = self._build_plan(
                    intent=intent, tool_name=tool_name, args=args,
                    risk_level=risk_level, original_text=sanitized, context=merged,
                )
                if plan_entry is None:
                    elapsed = time.monotonic() - start
                    return {
                        "ok": False,
                        "response": "No puedo crear un plan válido para esta solicitud.",
                        "intent": intent.intent_id,
                        "confidence": intent.confidence,
                        "needs_llm": intent.needs_llm,
                        "risk_level": risk_level.value,
                        "requires_confirmation": False,
                        "tool_result": {"ok": False, "code": "PLAN_INVALID", "message": "invalid plan", "data": {}},
                        "error": "PLAN_INVALID",
                        "elapsed_ms": round(elapsed * 1000),
                        "backend": type(self._backend_selector.active).__name__,
                    }
                plan, validation_errors = plan_entry
                if validation_errors:
                    elapsed = time.monotonic() - start
                    detail = "; ".join(validation_errors)
                    return {
                        "ok": False,
                        "response": f"No puedo crear un plan válido para esta solicitud. {detail}",
                        "intent": intent.intent_id,
                        "confidence": intent.confidence,
                        "needs_llm": intent.needs_llm,
                        "risk_level": risk_level.value,
                        "requires_confirmation": False,
                        "tool_result": {"ok": False, "code": "PLAN_INVALID", "message": detail, "data": {}},
                        "error": "PLAN_INVALID",
                        "elapsed_ms": round(elapsed * 1000),
                        "backend": type(self._backend_selector.active).__name__,
                    }
                public_plan = self._public_plan_from_plan(
                    plan, tool_name, args, risk_level, sanitized,
                    destructive=bool(getattr(defn, "destructive", False)) if defn else False,
                )
                confirmation = self._confirmation_policy.issue(
                    plan_id=plan.plan_id,
                    summary=f"{plan.title}: {len(plan.steps)} paso(s)",
                    affected_resources=tuple(str(v) for v in args.values()),
                    risks=plan.risks,
                    plan=plan,
                )
                self._pending_plans[plan.plan_id] = {
                    "plan": plan,
                    "confirmation_id": confirmation.confirmation_id,
                    "status": "pending",
                    "created_at": time.time(),
                    "original_text": sanitized,
                    "intent": intent.intent_id,
                    "tool": tool_name,
                    "args": dict(args),
                    "risk_level": risk_level.value,
                    "destructive": bool(getattr(defn, "destructive", False)) if defn else False,
                }
                self._record_trace(intent, context, [tool_name], [], start)
                elapsed = time.monotonic() - start
                return {
                    "ok": True,
                    "response": self._confirmation_request_text(public_plan),
                    "intent": intent.intent_id,
                    "confidence": intent.confidence,
                    "needs_llm": intent.needs_llm,
                    "risk_level": risk_level.value,
                    "requires_confirmation": True,
                    "plan_id": plan.plan_id,
                    "plan": public_plan,
                    "tool_result": None,
                    "elapsed_ms": round(elapsed * 1000),
                    "backend": type(self._backend_selector.active).__name__,
                }

            llm_response = self._generate_response(sanitized, intent, merged)
            tool_result = self._run_tool(tool_name, args, intent, merged) if tool_name else None
            # ADR-006: a failed tool is NEVER reported as ok. The outer "ok"
            # mirrors the tool outcome so the UI can distinguish real failure
            # from nominal success.
            tool_ok = bool(tool_result.ok) if tool_result is not None else True
            if tool_ok:
                response_text = llm_response or ""
            else:
                response_text = (tool_result.message
                                 or f"La operación falló ({tool_result.code}).")

            elapsed = time.monotonic() - start
            return {
                "ok": tool_ok,
                "response": response_text,
                "intent": intent.intent_id,
                "confidence": intent.confidence,
                "needs_llm": intent.needs_llm,
                "risk_level": risk_level.value,
                "requires_confirmation": False,
                "tool_result": {"ok": tool_result.ok, "code": tool_result.code, "message": tool_result.message, "data": tool_result.data} if tool_result else None,
                "error": tool_result.message if tool_result and not tool_ok else "",
                "elapsed_ms": round(elapsed * 1000),
                "backend": type(self._backend_selector.active).__name__,
            }

        except Exception as exc:
            logger.exception("AssistantRuntime.process_message failed")
            elapsed = time.monotonic() - start
            return {
                "ok": False,
                "response": str(exc),
                "intent": "error",
                "confidence": 0.0,
                "needs_llm": False,
                "risk_level": RiskLevel.SAFE.value,
                "requires_confirmation": False,
                "tool_result": None,
                "elapsed_ms": round(elapsed * 1000),
                "backend": type(self._backend_selector.active).__name__,
            }

    # ── Plan lifecycle ───────────────────────────────────────────────────

    def _build_plan(
        self, *, intent: IntentResult, tool_name: str, args: dict[str, Any],
        risk_level: RiskLevel, original_text: str, context: dict[str, Any],
    ) -> tuple[Any, list[str]] | None:
        """Build the ActionPlan through the runtime planner and validate it.

        Returns ``(plan, validation_errors)`` when a plan exists, or None
        when the intent has no plan template at all.
        """
        parsed = ParsedIntent(
            intent_id=intent.intent_id,
            confidence=intent.confidence,
            source="rules",
            entities=dict(intent.entities or {}),
            reasoning_summary=f"Intención {intent.intent_id} con confianza {intent.confidence:.2f}",
            requested_actions=(intent.intent_id,),
        )
        plan = self._planner.build_plan(parsed, {
            "selection": (context or {}).get("selection", {}),
        })
        if not plan.steps:
            return None
        # Align step arguments with the normalized intent entities so the
        # executor validates and runs the tool with the caller's values.
        steps = list(plan.steps)
        for i, step in enumerate(steps):
            if step.tool == tool_name:
                steps[i] = replace(step, arguments=args)
        plan = replace(plan, steps=tuple(steps))
        validation = self._validator.validate(plan)
        errors = list(validation.errors) if validation.status == "INVALID" else []
        return plan, errors

    def _public_plan_from_plan(
        self, plan: Any, tool_name: str, args: dict[str, Any],
        risk_level: RiskLevel, original_text: str, destructive: bool = False,
    ) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "action": original_text,
            "intent": plan.intent,
            "tool": tool_name,
            "args": dict(args),
            "risk_level": risk_level.value,
            "destructive": destructive,
            "requires_confirmation": True,
            "status": "pending",
        }

    @staticmethod
    def _confirmation_request_text(plan: dict[str, Any]) -> str:
        risk = plan["risk_level"]
        note = " Esta acción es destructiva y no se puede deshacer." if plan["destructive"] else ""
        return (
            f"La acción '{plan['tool']}' requiere tu confirmación (riesgo {risk})."
            f"{note} ¿Deseas continuar?"
        )

    def get_pending_plan(self, plan_id: str) -> dict[str, Any] | None:
        entry = self._pending_plans.get(plan_id)
        return self._public_plan(entry) if entry else None

    @property
    def pending_plans(self) -> list[dict[str, Any]]:
        return [self._public_plan(p) for p in self._pending_plans.values()]

    @property
    def plan_history(self) -> list[dict[str, Any]]:
        return list(self._plan_history)

    def _public_plan(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "plan_id": entry["plan"].plan_id,
            "action": entry["original_text"],
            "intent": entry["intent"],
            "tool": entry["tool"],
            "args": dict(entry["args"]),
            "risk_level": entry["risk_level"],
            "destructive": entry["destructive"],
            "requires_confirmation": True,
            "status": entry.get("status", "pending"),
        }

    def _record_plan(self, entry: dict[str, Any], result: dict[str, Any] | None = None) -> None:
        record = self._public_plan(entry)
        record["finished_at"] = time.time()
        if result is not None:
            record["result"] = result
        self._plan_history.append(record)
        if len(self._plan_history) > _MAX_PLAN_HISTORY:
            self._plan_history = self._plan_history[-_MAX_PLAN_HISTORY:]

    def confirm_plan(self, plan_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a previously planned action after explicit user acceptance."""
        entry = self._pending_plans.pop(plan_id, None)
        if entry is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        if self._cancelled:
            entry["status"] = "cancelled"
            self._record_plan(entry)
            return {"ok": False, "error": "CANCELLED", "plan_id": plan_id,
                    "response": "La acción fue cancelada."}

        validation = self._confirmation_policy.validate(
            entry["confirmation_id"], plan_id,
        )
        if not validation.ok:
            entry["status"] = "expired"
            return {"ok": False, "error": validation.code.value,
                    "plan_id": plan_id, "response": validation.message}

        # The confirmation was granted: clear the flag so the executor
        # actually runs the plan steps.
        plan = replace(entry["plan"], requires_confirmation=False)
        start = time.monotonic()
        token = CancellationSource().token
        result = self._executor.execute(plan, token)
        elapsed = time.monotonic() - start

        entry["status"] = "executed" if result.ok else "failed"
        step = result.step_results[0] if result.step_results else None
        result_payload = {
            "ok": result.ok,
            "code": result.code.value,
            "message": result.error,
            "data": step.data if step else {},
        }
        self._record_plan(entry, result_payload)
        self._record_trace(
            {"intent_id": entry["intent"], "confidence": 1.0, "needs_llm": False},
            context, [entry["tool"]],
            [result.code.value] if not result.ok else [],
            start,
        )

        if result.ok:
            response = f"Acción '{entry['tool']}' ejecutada correctamente."
        else:
            response = f"No se pudo ejecutar '{entry['tool']}': {result.error or result.code.value}"
        return {
            "ok": result.ok,
            "plan_id": plan_id,
            "tool": entry["tool"],
            "response": response,
            "tool_result": result_payload,
            "elapsed_ms": round(elapsed * 1000),
        }

    def reject_plan(self, plan_id: str) -> dict[str, Any]:
        """Discard a planned action because the user declined it."""
        entry = self._pending_plans.pop(plan_id, None)
        if entry is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        entry["status"] = "rejected"
        self._record_plan(entry)
        return {"ok": True, "status": "rejected", "plan_id": plan_id,
                "response": "Acción rechazada. No se realizó ningún cambio."}

    def cancel_plan(self, plan_id: str) -> dict[str, Any]:
        """Cancel a planned action (e.g. the user asked to cancel while pending)."""
        entry = self._pending_plans.pop(plan_id, None)
        if entry is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        entry["status"] = "cancelled"
        self._record_plan(entry)
        return {"ok": True, "status": "cancelled", "plan_id": plan_id,
                "response": "Confirmación cancelada. No se ejecutó la acción."}

    def cancel(self) -> None:
        self._cancelled = True
        self._backend_selector.active.cancel()

    # ── Context assembly ─────────────────────────────────────────────────

    def _assemble_context(self, caller_context: dict[str, Any] | None) -> dict[str, Any]:
        """Merge the runtime's governed context snapshot with caller context."""
        merged = dict(caller_context or {})
        try:
            snap = self._context_assembler.assemble_sanitized(
                privacy_level=PrivacyLevel.STANDARD,
            ).snapshot
            merged.setdefault("selection", snap.selection)
            merged.setdefault("playback", snap.playback)
            merged.setdefault("active_section", snap.active_section)
        except Exception:
            logger.debug("Runtime context assembly skipped: %s", exc_info=True)
        return merged

    # ── Response generation (backend selection) ──────────────────────────

    def _generate_response(self, sanitized: str, intent: IntentResult,
                           context: dict[str, Any] | None) -> str:
        llm_response: str | None = None
        active = self._backend_selector.auto_fallback()
        if intent.needs_llm and type(active).__name__ != "CalicoBackend":
            snapshot = self._privacy_guard.build_snapshot(context)
            provider_req = ProviderRequest(
                messages=[{"role": "user", "content": self._build_llm_prompt(sanitized, intent, snapshot)}],
            )
            try:
                provider_resp = active.generate(provider_req)
                if provider_resp.text:
                    validated = self._privacy_guard.validate_output(provider_resp.text)
                    llm_response = validated
            except Exception as exc:
                logger.warning("Backend generation failed, using Calico fallback: %s", exc)
                llm_response = None

        if not llm_response:
            lite_req = ProviderRequest(
                messages=[{"role": "user", "content": sanitized}],
            )
            lite_resp = self._lite_backend.generate(lite_req)
            llm_response = lite_resp.text
        return llm_response

    def _build_llm_prompt(self, text: str, intent: IntentResult, snapshot: SanitizedSnapshot) -> str:
        safe = snapshot.to_dict()
        context_block = ""
        if safe:
            items = []
            for k, v in safe.items():
                if isinstance(v, list):
                    items.append(f"{k}: {len(v)} elementos")
                elif isinstance(v, dict):
                    items.append(f"{k}: {', '.join(f'{kk}={vv}' for kk, vv in list(v.items())[:3])}")
                else:
                    items.append(f"{k}: {v}")
            context_block = "\nContexto actual:\n" + "\n".join(items) if items else ""

        return (
            "Eres Michi AI, un asistente especializado exclusivamente en un reproductor de música llamado Michi Music Player. "
            "Solo puedes hablar de música, biblioteca musical, audio, diagnóstico de audio, "
            "y el ecosistema Michi (dispositivos, servidores, sincronización). "
            "No respondes preguntas de otros temas. Cuando no sepas o el tema esté fuera de tu ámbito, "
            "responde 'Eso está fuera de mi ámbito. ¿Quieres que te ayude con tu biblioteca musical?'.\n\n"
            f"Intención detectada: {intent.intent_id}\n"
            f"Mensaje del usuario: {text}{context_block}\n\n"
            "Responde de forma clara y en español."
        )

    def get_suggestions(self, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
        # Actions are natural-language phrases the IntentRouter recognizes and
        # that map to tools actually registered in ToolRegistryV2. Routes must
        # exist in ui_qml_bridge/route_registry.py (aliases allowed).
        return [
            {"title": "Reproducir algo de jazz", "description": "Busca jazz en tu biblioteca", "action": "busca jazz", "route": ""},
            {"title": "¿Qué está sonando?", "description": "Muestra la cola de reproducción actual", "action": "que suena ahora", "route": "nowplaying"},
            {"title": "Diagnosticar sistema", "description": "Revisa el estado del ecosistema Michi", "action": "diagnostica el sistema", "route": ""},
        ]

    # ── Tool execution through the governed registry/executor ────────────

    def _run_tool(self, tool_name: str, args: dict[str, Any],
                  intent: IntentResult | None = None,
                  context: dict[str, Any] | None = None) -> ToolResult | None:
        if not tool_name:
            return None
        plan = self._planner.build_plan(
            ParsedIntent(
                intent_id=intent.intent_id if intent else tool_name,
                confidence=1.0,
                source="runtime",
                entities=dict(args),
            ),
            {"selection": (context or {}).get("selection", {})},
        )
        if not plan.steps:
            steps = (PlanStep(step_id="step_0", tool=tool_name, arguments=args),)
        else:
            steps = list(plan.steps)
            for i, step in enumerate(steps):
                if step.tool == tool_name:
                    steps[i] = replace(step, arguments=args)
            steps = tuple(steps)
        plan = replace(plan, requires_confirmation=False, steps=steps)
        token = CancellationSource().token
        try:
            result = self._executor.execute(plan, token)
        except Exception as exc:
            logger.debug("Tool execution failed for %s: %s", tool_name, exc)
            return ToolResult(ok=False, code="EXECUTION_ERROR", message=str(exc))
        if result.step_results:
            step = result.step_results[0]
            return ToolResult(
                ok=bool(step.ok),
                code=str(step.code.value),
                message=step.error or "",
                data=step.data if isinstance(step.data, dict) else {},
            )
        return ToolResult(ok=result.ok, code=str(result.code.value),
                          message=result.error or "", data={})

    @staticmethod
    def _tool_arguments(tool_name: str, intent: IntentResult) -> dict[str, Any]:
        """Normalize intent entities into the argument schema the tool expects."""
        args: dict[str, Any] = dict(intent.entities) if intent.entities else {}
        if tool_name == "search_library" and "query" not in args:
            for key in ("artist", "album", "genre"):
                if args.get(key):
                    args["query"] = args[key]
                    break
        if tool_name == "create_smart_mix" and "genre" in args:
            args.setdefault("strategy", "by_genre")
        if tool_name == "set_volume" and "volume" in args:
            try:
                args["volume"] = max(0, min(100, int(args["volume"])))
            except (TypeError, ValueError):
                args.pop("volume", None)
        return args

    def _intent_to_tool(self, intent_id: str) -> str | None:
        # Intent -> canonical V2 tool name. Every value MUST be a tool actually
        # registered in ToolRegistryV2 (see register_builtin_tools); mapping to
        # a non-existent tool silently breaks execution. Validated by
        # tests/qml/ai/test_michi_ai_tool_mapping.py.
        mapping: dict[str, str] = {
            "search_library": "search_library",
            "search_artist": "search_library",
            "search_album": "search_library",
            "search_genre": "search_library",
            "playback_play": "resume",
            "playback_pause": "pause",
            "playback_next": "next",
            "playback_prev": "previous",
            "playback_volume": "set_volume",
            "playback_info": "get_queue",
            "diagnosis": "diagnose_ecosystem",
            "suggestion": "create_smart_mix",
            "library_info": "scan_library_health",
            "navigate": "navigate",
            "create_playlist": "create_playlist",
            "delete_playlist": "delete_playlist",
            "apply_library_repair": "apply_library_repair",
            "restore_setting": "restore_setting",
        }
        return mapping.get(intent_id)

    # ── Trace recording ──────────────────────────────────────────────────

    def _record_trace(self, intent: IntentResult | dict[str, Any], context: dict[str, Any] | None,
                      tools: list[str], result_codes: list[str], start: float) -> None:
        if not self._trace_enabled or self._trace_recorder is None:
            return
        try:
            intent_id = intent.get("intent_id") if isinstance(intent, dict) else intent.intent_id
            trace = AssistantTrace(
                trace_id=uuid.uuid4().hex[:16],
                session_id="",
                request_id=uuid.uuid4().hex[:12],
                intent=str(intent_id),
                provider="runtime",
                tools=tuple(tools),
                durations={"total": (time.monotonic() - start) * 1000},
                result_codes=tuple(result_codes),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._trace_recorder.record(trace)
        except Exception as e:
            logger.debug("Trace recording failed: %s", e)
