from __future__ import annotations

from typing import Any

from michi_ai.v2.core.models import (
    ActionPlan, AssistantResponse, AssistantResponseType, PlanExecutionResult,
    ParsedIntent,
)


class ResponseComposer:
    def compose_answer(self, message: str, title: str = "", details: str = "") -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.ANSWER,
            title=title or "Respuesta",
            message=message,
            details=details,
        )

    def compose_clarification(self, question: str, intent: ParsedIntent | None = None) -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.CLARIFICATION,
            title="Necesito más información",
            message=question,
            details=intent.reasoning_summary if intent else "",
        )

    def compose_plan_preview(self, plan: ActionPlan) -> AssistantResponse:
        steps = []
        for i, step in enumerate(plan.steps):
            steps.append({
                "step": i + 1,
                "tool": step.tool,
                "description": self._describe_tool(step.tool),
            })

        return AssistantResponse(
            type=AssistantResponseType.PLAN_PREVIEW,
            title=f"Plan: {plan.title}",
            message=self._format_plan_summary(plan),
            details=self._format_plan_details(plan),
            actions=tuple(steps),
            plan=plan,
        )

    def compose_confirmation_request(
        self, plan: ActionPlan,
        summary: str = "",
        affected: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
    ) -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.CONFIRMATION_REQUEST,
            title="¿Confirmas esta acción?",
            message=summary or f"Se ejecutará: {plan.title}",
            details=self._format_confirmation_details(plan, affected, risks),
            plan=plan,
        )

    def compose_execution_progress(self, plan_id: str, current: int, total: int, state: str) -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.EXECUTION_PROGRESS,
            title="Ejecutando plan...",
            message=f"Paso {current}/{total}",
            progress={"plan_id": plan_id, "current": current, "total": total, "state": state},
        )

    def compose_execution_result(self, result: PlanExecutionResult) -> AssistantResponse:
        if result.ok:
            return AssistantResponse(
                type=AssistantResponseType.EXECUTION_RESULT,
                title="Plan completado",
                message="El plan se ejecutó correctamente.",
                details=self._format_execution_details(result),
            )
        return AssistantResponse(
            type=AssistantResponseType.ERROR,
            title="Error en ejecución",
            message=result.error or "El plan no pudo completarse.",
            details=self._format_execution_details(result),
        )

    def compose_error(self, error: str, title: str = "Error") -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.ERROR,
            title=title,
            message=error,
        )

    def compose_suggestion(self, title: str, message: str, actions: tuple[dict[str, Any], ...] = ()) -> AssistantResponse:
        return AssistantResponse(
            type=AssistantResponseType.SUGGESTION,
            title=title,
            message=message,
            actions=actions,
        )

    def _describe_tool(self, tool_name: str) -> str:
        descriptions: dict[str, str] = {
            "play_track": "Reproducir canción",
            "play_album": "Reproducir álbum",
            "play_artist": "Reproducir artista",
            "play_playlist": "Reproducir playlist",
            "pause": "Pausar reproducción",
            "resume": "Reanudar reproducción",
            "stop": "Detener reproducción",
            "next": "Siguiente canción",
            "previous": "Canción anterior",
            "seek": "Avanzar/retroceder",
            "set_volume": "Ajustar volumen",
            "add_to_queue": "Agregar a la cola",
            "clear_queue": "Limpiar cola",
            "create_playlist": "Crear playlist",
            "create_smart_mix": "Crear mix inteligente",
            "search_library": "Buscar en biblioteca",
            "scan_library_health": "Diagnosticar biblioteca",
            "apply_library_repair": "Reparar biblioteca",
            "recommend_conversion_profile": "Recomendar perfil de conversión",
            "preview_conversion": "Vista previa de conversión",
            "start_conversion": "Iniciar conversión",
            "diagnose_ecosystem": "Diagnosticar ecosistema",
            "plan_device_sync": "Planificar sincronización",
            "start_device_sync": "Iniciar sincronización",
        }
        return descriptions.get(tool_name, tool_name)

    def _format_plan_summary(self, plan: ActionPlan) -> str:
        parts = [f"Se ejecutarán {len(plan.steps)} paso(s):"]
        for i, step in enumerate(plan.steps):
            parts.append(f"  {i + 1}. {self._describe_tool(step.tool)}")
        if plan.risks:
            parts.append("Riesgos: " + ", ".join(plan.risks))
        return "\n".join(parts)

    def _format_plan_details(self, plan: ActionPlan) -> str:
        return f"ID: {plan.plan_id} | Intención: {plan.intent} | Pasos: {len(plan.steps)}"

    def _format_confirmation_details(self, plan: ActionPlan, affected: tuple[str, ...], risks: tuple[str, ...]) -> str:
        parts = []
        if affected:
            parts.append("Recursos afectados: " + ", ".join(affected))
        if risks:
            parts.append("Riesgos: " + ", ".join(risks))
        parts.append("Este plan requiere confirmación antes de ejecutarse.")
        return "\n".join(parts)

    def _format_execution_details(self, result: PlanExecutionResult) -> str:
        if result.ok:
            return f"Completado en {result.duration_ms:.0f}ms con {len(result.step_results)} pasos."
        return f"Falló en {result.duration_ms:.0f}ms: {result.error}"
