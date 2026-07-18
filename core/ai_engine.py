from __future__ import annotations

import logging
import time
from typing import Any

from michi_ai.v2.core.models import ProviderRequest
from michi_ai.tools.tool_registry import ToolRegistry, ToolResult

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
        tool_registry: ToolRegistry | None = None,
        intent_router: IntentRouter | None = None,
        risk_policy: RiskPolicy | None = None,
        privacy_guard: PrivacyGuard | None = None,
        backend_selector: BackendSelector | None = None,
    ) -> None:
        self._lite_backend = CalicoBackend()
        self._backend_selector = backend_selector or BackendSelector()
        self._tool_registry = tool_registry or ToolRegistry()
        self._intent_router = intent_router or IntentRouter()
        self._risk_policy = risk_policy or RiskPolicy()
        self._privacy_guard = privacy_guard or PrivacyGuard()
        self._cancelled = False

    @property
    def active_backend(self) -> LocalModelBackend:
        return self._backend_selector.active

    def set_active_backend(self, name: str) -> None:
        self._backend_selector.set_active(name)

    @property
    def backend_selector(self) -> BackendSelector:
        return self._backend_selector

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def process_message(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._cancelled = False
        start = time.monotonic()

        try:
            sanitized = self._privacy_guard.sanitize_input(text)
            intent: IntentResult = self._intent_router.detect(sanitized, context)

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

            tool_result = self._execute_tool(intent, context)

            risk_level = RiskLevel.SAFE
            if tool_result and tool_result.ok:
                risk_level = self._risk_policy.assess(
                    intent.intent_id,
                    resources=tool_result.data if isinstance(tool_result.data, list) else None,
                )

            elapsed = time.monotonic() - start
            return {
                "ok": True,
                "response": llm_response or "",
                "intent": intent.intent_id,
                "confidence": intent.confidence,
                "needs_llm": intent.needs_llm,
                "risk_level": risk_level.value,
                "requires_confirmation": self._risk_policy.require_confirmation(risk_level),
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

    def cancel(self) -> None:
        self._cancelled = True
        self._backend_selector.active.cancel()

    def get_suggestions(self, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
        return [
            {"title": "Reproducir algo de jazz", "description": "Busca jazz en tu biblioteca", "action": "play_genre", "route": ""},
            {"title": "¿Qué está sonando?", "description": "Muestra la canción actual", "action": "now_playing", "route": "playback"},
            {"title": "Diagnosticar sistema", "description": "Revisa el estado del sistema", "action": "diagnose", "route": ""},
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
        try:
            return self._tool_registry.execute(tool_name, params=intent.entities if intent.entities else None)
        except Exception as exc:
            logger.debug("Tool execution failed for %s: %s", tool_name, exc)
            return ToolResult(ok=False, code="EXECUTION_ERROR", message=str(exc))

    def _intent_to_tool(self, intent_id: str) -> str | None:
        mapping: dict[str, str] = {
            "search_library": "search_library",
            "search_artist": "search_artist",
            "search_album": "search_album",
            "search_genre": "search_genre",
            "playback_play": "playback_play",
            "playback_pause": "playback_pause",
            "playback_next": "playback_next",
            "playback_prev": "playback_prev",
            "playback_volume": "playback_set_volume",
            "playback_info": "playback_get_state",
            "diagnosis": "diagnostics_check",
            "suggestion": "get_recommendations",
            "library_info": "library_get_stats",
            "navigate": "navigate_to",
        }
        return mapping.get(intent_id)
