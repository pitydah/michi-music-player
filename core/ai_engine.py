from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from michi_ai.v2.core.models import ProviderRequest
from michi_ai.tools.tool_result import ToolResult
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

from core.ai.backends.base import LocalModelBackend
from core.ai.backends.calico import CalicoBackend
from core.ai.backend_selector import BackendSelector
from core.ai.intent_router import IntentRouter, IntentResult
from core.ai.privacy_guard import PrivacyGuard, SanitizedSnapshot
from core.ai.risk_policy import RiskLevel, RiskPolicy

logger = logging.getLogger("michi.ai_engine")


class MichiAIEngine:
    def __init__(
        self,
        tool_registry: ToolRegistryV2 | None = None,
        intent_router: IntentRouter | None = None,
        risk_policy: RiskPolicy | None = None,
        privacy_guard: PrivacyGuard | None = None,
        backend_selector: BackendSelector | None = None,
    ) -> None:
        self._lite_backend = CalicoBackend()
        self._backend_selector = backend_selector or BackendSelector()
        # The engine must execute through the canonical V2 tool registry. When
        # none is injected it falls back to an empty V2 registry (no legacy
        # ToolRegistry) so the V2 architecture is what actually runs.
        self._tool_registry = tool_registry or ToolRegistryV2()
        self._intent_router = intent_router or IntentRouter()
        self._risk_policy = risk_policy or RiskPolicy()
        self._privacy_guard = privacy_guard or PrivacyGuard()
        self._cancelled = False
        # Plans awaiting explicit user confirmation. A destructive or
        # confirmation-required tool NEVER runs before confirm_plan() is
        # called with the matching plan_id.
        self._pending_plans: dict[str, dict[str, Any]] = {}
        self._plan_history: list[dict[str, Any]] = []

    @property
    def active_backend(self) -> LocalModelBackend:
        return self._backend_selector.active

    def set_active_backend(self, name: str) -> None:
        self._backend_selector.set_active(name)

    @property
    def backend_selector(self) -> BackendSelector:
        return self._backend_selector

    @property
    def tool_registry(self) -> ToolRegistryV2:
        return self._tool_registry

    def process_message(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Canonical flow: detect intent → resolve tool → validate args →
        evaluate risk → build plan → request confirmation → execute after
        accept → record result.

        A tool whose definition requires confirmation (or whose risk level is
        MODERATE/CRITICAL) is NEVER executed inside this method. It returns a
        pending plan instead; execution only happens via confirm_plan().
        """
        self._cancelled = False
        start = time.monotonic()

        try:
            sanitized = self._privacy_guard.sanitize_input(text)
            intent: IntentResult = self._intent_router.detect(sanitized, context)

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
                plan = self._build_plan(plan_id=self._new_plan_id(), intent=intent,
                                        tool_name=tool_name, args=args, defn=defn,
                                        risk_level=risk_level, original_text=sanitized)
                self._pending_plans[plan["plan_id"]] = plan
                elapsed = time.monotonic() - start
                return {
                    "ok": True,
                    "response": self._confirmation_request_text(plan),
                    "intent": intent.intent_id,
                    "confidence": intent.confidence,
                    "needs_llm": intent.needs_llm,
                    "risk_level": risk_level.value,
                    "requires_confirmation": True,
                    "plan_id": plan["plan_id"],
                    "plan": self._public_plan(plan),
                    "tool_result": None,
                    "elapsed_ms": round(elapsed * 1000),
                    "backend": type(self._backend_selector.active).__name__,
                }

            llm_response = self._generate_response(sanitized, intent, context)
            tool_result = self._run_tool(tool_name, args) if tool_name else None

            elapsed = time.monotonic() - start
            return {
                "ok": True,
                "response": llm_response or "",
                "intent": intent.intent_id,
                "confidence": intent.confidence,
                "needs_llm": intent.needs_llm,
                "risk_level": risk_level.value,
                "requires_confirmation": False,
                "tool_result": {"ok": tool_result.ok, "code": tool_result.code, "message": tool_result.message, "data": tool_result.data} if tool_result else None,
                "elapsed_ms": round(elapsed * 1000),
                "backend": type(self._backend_selector.active).__name__,
            }

        except Exception as exc:
            logger.exception("AIEngine.process_message failed")
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

    # ── Plan lifecycle ─────────────────────────────────────────────────

    @staticmethod
    def _new_plan_id() -> str:
        return f"plan-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _build_plan(*, plan_id: str, intent: IntentResult, tool_name: str,
                    args: dict[str, Any], defn: Any, risk_level: RiskLevel,
                    original_text: str) -> dict[str, Any]:
        return {
            "plan_id": plan_id,
            "intent": intent.intent_id,
            "tool": tool_name,
            "args": dict(args),
            "risk_level": risk_level.value,
            "requires_confirmation": True,
            "destructive": bool(getattr(defn, "destructive", False)),
            "original_text": original_text,
            "status": "pending",
            "created_at": time.time(),
        }

    @staticmethod
    def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "plan_id": plan["plan_id"],
            "action": plan["original_text"],
            "intent": plan["intent"],
            "tool": plan["tool"],
            "args": dict(plan["args"]),
            "risk_level": plan["risk_level"],
            "destructive": plan["destructive"],
            "requires_confirmation": True,
            "status": plan["status"],
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
        plan = self._pending_plans.get(plan_id)
        return self._public_plan(plan) if plan else None

    @property
    def pending_plans(self) -> list[dict[str, Any]]:
        return [self._public_plan(p) for p in self._pending_plans.values()]

    @property
    def plan_history(self) -> list[dict[str, Any]]:
        return list(self._plan_history)

    def _record_plan(self, plan: dict[str, Any], result: dict[str, Any] | None = None) -> None:
        entry = self._public_plan(plan)
        entry["finished_at"] = time.time()
        if result is not None:
            entry["result"] = result
        self._plan_history.append(entry)

    def confirm_plan(self, plan_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a previously planned action after explicit user acceptance."""
        plan = self._pending_plans.pop(plan_id, None)
        if plan is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        if self._cancelled:
            plan["status"] = "cancelled"
            self._record_plan(plan)
            return {"ok": False, "error": "CANCELLED", "plan_id": plan_id,
                    "response": "La acción fue cancelada."}

        start = time.monotonic()
        tool_result = self._run_tool(plan["tool"], plan["args"])
        elapsed = time.monotonic() - start

        plan["status"] = "executed" if tool_result.ok else "failed"
        result_payload = {"ok": tool_result.ok, "code": tool_result.code,
                          "message": tool_result.message, "data": tool_result.data}
        self._record_plan(plan, result_payload)

        if tool_result.ok:
            response = f"Acción '{plan['tool']}' ejecutada correctamente."
        else:
            response = f"No se pudo ejecutar '{plan['tool']}': {tool_result.message or tool_result.code}"
        return {
            "ok": tool_result.ok,
            "plan_id": plan_id,
            "tool": plan["tool"],
            "response": response,
            "tool_result": result_payload,
            "elapsed_ms": round(elapsed * 1000),
        }

    def reject_plan(self, plan_id: str) -> dict[str, Any]:
        """Discard a planned action because the user declined it."""
        plan = self._pending_plans.pop(plan_id, None)
        if plan is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        plan["status"] = "rejected"
        self._record_plan(plan)
        return {"ok": True, "status": "rejected", "plan_id": plan_id,
                "response": "Acción rechazada. No se realizó ningún cambio."}

    def cancel_plan(self, plan_id: str) -> dict[str, Any]:
        """Cancel a planned action (e.g. the user asked to cancel while pending)."""
        plan = self._pending_plans.pop(plan_id, None)
        if plan is None:
            return {"ok": False, "error": "PLAN_NOT_FOUND", "plan_id": plan_id,
                    "response": "No hay ninguna acción pendiente con ese identificador."}
        plan["status"] = "cancelled"
        self._record_plan(plan)
        return {"ok": True, "status": "cancelled", "plan_id": plan_id,
                "response": "Confirmación cancelada. No se ejecutó la acción."}

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

    def cancel(self) -> None:
        self._cancelled = True
        self._backend_selector.active.cancel()

    def get_suggestions(self, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
        # Actions are natural-language phrases the IntentRouter recognizes and
        # that map to tools actually registered in ToolRegistryV2. Routes must
        # exist in ui_qml_bridge/route_registry.py (aliases allowed).
        return [
            {"title": "Reproducir algo de jazz", "description": "Busca jazz en tu biblioteca", "action": "busca jazz", "route": ""},
            {"title": "¿Qué está sonando?", "description": "Muestra la cola de reproducción actual", "action": "que suena ahora", "route": "nowplaying"},
            {"title": "Diagnosticar sistema", "description": "Revisa el estado del ecosistema Michi", "action": "diagnostica el sistema", "route": ""},
        ]

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

    def _execute_tool(self, intent: IntentResult, context: dict[str, Any] | None = None) -> ToolResult | None:
        tool_name = self._intent_to_tool(intent.intent_id)
        if not tool_name:
            return None
        arguments = self._tool_arguments(tool_name, intent)
        return self._run_tool(tool_name, arguments)

    def _run_tool(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolResult:
        try:
            result = self._tool_registry.execute(tool_name, arguments=args or None)
            data = result.data if isinstance(result.data, dict) else {}
            return ToolResult(
                ok=bool(result.ok),
                code=str(result.code.value),
                message=result.error or "",
                data=data,
            )
        except Exception as exc:
            logger.debug("Tool execution failed for %s: %s", tool_name, exc)
            return ToolResult(ok=False, code="EXECUTION_ERROR", message=str(exc))

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
