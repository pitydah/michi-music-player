from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from michi_ai.v2.context.context_assembler import ContextAssembler
from michi_ai.v2.conversation.conversation_service import ConversationService
from michi_ai.v2.core.cancellation import CancellationSource, CancellationTokenRegistry
from michi_ai.v2.core.models import (
    ActionPlan, AssistantRequest, AssistantResponse, AssistantTrace, ContextSnapshot,
    ConversationTurn, OperationResult, ParsedIntent,
    PlanState, PrivacyLevel,
    ProviderRequest, ProviderType,
)
from michi_ai.v2.core.response_composer import ResponseComposer
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.intent.intent_router_v2 import IntentRouterV2
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.provider.provider_router import ProviderRouter
from michi_ai.v2.suggest.suggestion_engine_v2 import SuggestionEngineV2
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
from michi_ai.v2.trace.trace_recorder import TraceRecorder

logger = logging.getLogger(__name__)


class AssistantCoreService:
    def __init__(
        self,
        intent_router: IntentRouterV2 | None = None,
        context_assembler: ContextAssembler | None = None,
        tool_registry: ToolRegistryV2 | None = None,
        capability_resolver: CapabilityResolver | None = None,
        plan_builder: PlanBuilderV2 | None = None,
        plan_validator: PlanValidator | None = None,
        plan_executor: PlanExecutorV2 | None = None,
        confirmation_policy: ConfirmationPolicyV2 | None = None,
        provider_router: ProviderRouter | None = None,
        conversation_service: ConversationService | None = None,
        suggestion_engine: SuggestionEngineV2 | None = None,
        trace_recorder: TraceRecorder | None = None,
        response_composer: ResponseComposer | None = None,
    ) -> None:
        self.intent_router = intent_router or IntentRouterV2()
        self.context_assembler = context_assembler or ContextAssembler()
        self.tool_registry = tool_registry or ToolRegistryV2()
        self.capability_resolver = capability_resolver or self.tool_registry.capability_resolver
        self.plan_builder = plan_builder or PlanBuilderV2(self.tool_registry, self.capability_resolver)
        self.plan_validator = plan_validator or PlanValidator(self.tool_registry, self.capability_resolver)
        self.plan_executor = plan_executor or PlanExecutorV2(self.tool_registry)
        self.confirmation_policy = confirmation_policy or ConfirmationPolicyV2()
        self.provider_router = provider_router or ProviderRouter()
        self.conversation_service = conversation_service or ConversationService()
        self.suggestion_engine = suggestion_engine or SuggestionEngineV2()
        self.trace_recorder = trace_recorder or TraceRecorder()
        self.response_composer = response_composer or ResponseComposer()

        self._cancellation_registry = CancellationTokenRegistry()
        self._current_request_id: str = ""
        self._initialized = False

        self._gateways: dict[str, Any] = {}

    def register_gateway(self, name: str, gateway: Any) -> None:
        self._gateways[name] = gateway

    def register_gateways(self, gateways: dict[str, Any]) -> None:
        self._gateways.update(gateways)

    def initialize(self) -> OperationResult[None]:
        self.capability_resolver.register_from_gateways(self._gateways)
        PrivacyLevel.LOCAL_FULL if self._is_local_only() else PrivacyLevel.STANDARD
        self._initialized = True
        return OperationResult.success(message="AssistantCoreService initialized")

    def _is_local_only(self) -> bool:
        return self.provider_router.active in (ProviderType.RULE, ProviderType.LOCAL_MODEL)

    async def process_message_async(self, request: AssistantRequest) -> AssistantResponse:
        return self.process_message(request)

    def process_message(self, request: AssistantRequest) -> AssistantResponse:
        correlation_id = request.correlation_id or uuid.uuid4().hex[:12]
        self._current_request_id = correlation_id
        start = datetime.now(timezone.utc)

        if not self._initialized:
            init = self.initialize()
            if not init.ok:
                return self.response_composer.compose_error(
                    f"Initialization failed: {init.message}",
                )

        session_result = self._get_or_create_session(request.session_id)
        if not session_result.ok or session_result.data is None:
            return self.response_composer.compose_error("Failed to create session")
        session = session_result.data
        session_id = session.session_id

        conversation_turn = ConversationTurn(role="user", content=request.text)
        self.conversation_service.add_turn(session_id, conversation_turn)

        sanitized = self.context_assembler.assemble_sanitized(
            session_id=session_id,
            privacy_level=PrivacyLevel.STANDARD,
        )
        context = sanitized.snapshot

        intent = self.intent_router.detect(request.text, {
            "active_section": context.active_section,
            "selection": context.selection,
            "playback": context.playback,
        })

        if intent.requires_clarification:
            assistant_turn = ConversationTurn(
                role="assistant",
                content=intent.clarification_question,
                metadata={"intent_id": intent.intent_id, "requires_clarification": True},
            )
            self.conversation_service.add_turn(session_id, assistant_turn)
            self._record_trace(session_id, intent, context, [], [], correlation_id, start)
            return self.response_composer.compose_clarification(
                intent.clarification_question, intent,
            )

        if intent.intent_id == "unknown" and intent.confidence < 0.5:
            provider_request = ProviderRequest(
                messages=tuple(self._build_provider_messages(session_id, request.text)),
                correlation_id=correlation_id,
            )
            provider_response = self.provider_router.chat(provider_request)
            if provider_response.text:
                assistant_turn = ConversationTurn(
                    role="assistant",
                    content=provider_response.text,
                    metadata={"provider": provider_response.provider},
                )
                self.conversation_service.add_turn(session_id, assistant_turn)
                self._record_trace(session_id, intent, context, [], [], correlation_id, start, provider=provider_response.provider)
                return self.response_composer.compose_answer(provider_response.text)

            assistant_turn = ConversationTurn(
                role="assistant", content="I couldn't process that request.",
            )
            self.conversation_service.add_turn(session_id, assistant_turn)
            return self.response_composer.compose_answer(
                "No entendí tu solicitud. ¿Podrías reformularla?",
            )

        needed_caps = CapabilityResolver.intent_to_capabilities(intent.intent_id)
        caps = self.capability_resolver.resolve(needed_caps)
        unavailable = [k for k, v in caps.items() if not v.available]
        if unavailable:
            self._record_trace(session_id, intent, context, [], [f"capabilities_unavailable:{','.join(unavailable)}"], correlation_id, start)
            return self.response_composer.compose_error(
                f"No tengo acceso a: {', '.join(unavailable)}. "
                "Esta funcionalidad no está disponible actualmente.",
            )

        plan = self.plan_builder.build_plan(intent, {
            "selection": context.selection,
            "playback": context.playback,
        }, session_id=session_id)

        validation = self.plan_validator.validate(plan)
        if validation.status == "INVALID":
            self._record_trace(session_id, intent, context, [], [f"plan_invalid:{','.join(validation.errors)}"], correlation_id, start)
            return self.response_composer.compose_error(
                "No puedo crear un plan válido para esta solicitud.\n" +
                "\n".join(validation.errors),
            )

        if plan.requires_confirmation or intent.requires_confirmation:
            affected = []
            for step in plan.steps:
                if step.arguments:
                    affected.extend(str(v) for v in step.arguments.values())

            confirmation_request = self.confirmation_policy.issue(
                plan_id=plan.plan_id,
                summary=f"{plan.title}: {len(plan.steps)} paso(s)",
                affected_resources=tuple(affected),
                risks=plan.risks,
                plan=plan,
            )
            session.pending_plan = plan.plan_id
            session.pending_confirmation = confirmation_request.confirmation_id
            self.conversation_service.set_pending_plan(session_id, plan.plan_id)

            self._record_trace(session_id, intent, context, [s.tool for s in plan.steps], [], correlation_id, start)
            return self.response_composer.compose_plan_preview(plan)

        return self._execute_and_respond(plan, session_id, intent, context, correlation_id, start)

    def confirm_plan(self, confirmation_id: str, session_id: str) -> AssistantResponse:
        session_result = self.conversation_service.get_session(session_id)
        if not session_result.ok or session_result.data is None:
            return self.response_composer.compose_error("Session not found")

        session = session_result.data
        pending_plan_id = session.pending_plan
        if not pending_plan_id:
            return self.response_composer.compose_error("No pending plan")

        plan = self.plan_executor.get_execution(pending_plan_id)
        if plan is None:
            plan_obj = getattr(session, 'pending_plan_obj', None)
            if plan_obj is None or not isinstance(plan_obj, ActionPlan):
                plan_obj = ActionPlan(plan_id=pending_plan_id, session_id=session_id)
        else:
            plan_obj = plan.plan

        validation = self.confirmation_policy.validate(confirmation_id, pending_plan_id)
        if not validation.ok:
            return self.response_composer.compose_error(
                validation.message or "Confirmation expired or invalid",
            )

        session.pending_plan = None
        session.pending_confirmation = None
        self.conversation_service.clear_pending_plan(session_id)

        start = datetime.now(timezone.utc)
        intent = ParsedIntent(intent_id=plan_obj.intent, confidence=1.0, source="confirmation")
        context = self.context_assembler.assemble(session_id=session_id)
        return self._execute_and_respond(
            plan_obj, session_id, intent, context,
            uuid.uuid4().hex[:12], start,
        )

    def cancel_plan(self, session_id: str) -> AssistantResponse:
        session_result = self.conversation_service.get_session(session_id)
        if not session_result.ok or session_result.data is None:
            return self.response_composer.compose_error("Session not found")

        session = session_result.data
        pending_plan_id = session.pending_plan
        if pending_plan_id:
            self.plan_executor.cancel(pending_plan_id, "cancelled by user")
            session.pending_plan = None
            session.pending_confirmation = None
            self.conversation_service.clear_pending_plan(session_id)
            return self.response_composer.compose_answer("Plan cancelado.")

        return self.response_composer.compose_answer("No hay un plan pendiente para cancelar.")

    def cancel_execution(self, plan_id: str) -> bool:
        return self.plan_executor.cancel(plan_id)

    def get_suggestions(self, session_id: str = "") -> list[Any]:
        snapshot = self.context_assembler.assemble(session_id=session_id)
        caps = self.capability_resolver.available()
        cap_bools = {k: True for k in caps}
        return self.suggestion_engine.generate(snapshot, cap_bools)

    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        return self.suggestion_engine.dismiss(suggestion_id)

    def get_session(self, session_id: str) -> OperationResult[Any]:
        return self.conversation_service.get_session(session_id)

    def create_session(self) -> OperationResult[Any]:
        return self.conversation_service.create_session()

    def clear_history(self, session_id: str) -> OperationResult[None]:
        return self.conversation_service.clear_history(session_id)

    def get_tools(self) -> list[Any]:
        return self.tool_registry.list_tools()

    def _get_or_create_session(self, session_id: str) -> OperationResult[Any]:
        if session_id:
            result = self.conversation_service.get_session(session_id)
            if result.ok:
                return result
        return self.conversation_service.create_session({"source": "assistant_core"})

    def _execute_and_respond(
        self, plan: ActionPlan, session_id: str,
        intent: ParsedIntent, context: ContextSnapshot,
        correlation_id: str, start: datetime,
    ) -> AssistantResponse:
        exec_cancellation = CancellationSource()
        self._cancellation_registry.register(plan.plan_id, exec_cancellation)
        result = self.plan_executor.execute(plan, exec_cancellation.token)
        self._cancellation_registry.remove(plan.plan_id)

        tool_names = [s.tool for s in plan.steps]
        result_codes = [r.code.value for r in result.step_results]
        self._record_trace(
            session_id, intent, context, tool_names, result_codes,
            correlation_id, start,
        )

        if result.state == PlanState.AWAITING_CONFIRMATION:
            session = self.conversation_service.get_session(session_id)
            if session.ok and session.data:
                session.data.pending_plan = plan.plan_id
            return self.response_composer.compose_plan_preview(plan)

        if result.state == PlanState.SUCCEEDED:
            assistant_turn = ConversationTurn(
                role="assistant",
                content=f"Plan completado: {plan.title}",
                tool_name=",".join(tool_names),
                tool_result={"state": "succeeded", "steps": len(result.step_results)},
            )
            self.conversation_service.add_turn(session_id, assistant_turn)
            return self.response_composer.compose_execution_result(result)

        if result.state == PlanState.PARTIAL_SUCCESS:
            assistant_turn = ConversationTurn(
                role="assistant",
                content=f"Plan completado parcialmente: {plan.title}",
                tool_result={"state": "partial", "error": result.error},
            )
            self.conversation_service.add_turn(session_id, assistant_turn)
            return self.response_composer.compose_execution_result(result)

        if result.state == PlanState.CANCELLED:
            return self.response_composer.compose_answer(
                result.error or "El plan fue cancelado.",
            )

        if result.state == PlanState.ROLLED_BACK:
            assistant_turn = ConversationTurn(
                role="assistant",
                content=f"Plan revertido: {result.error or 'rollback completado'}",
            )
            self.conversation_service.add_turn(session_id, assistant_turn)
            return self.response_composer.compose_answer(
                "El plan falló y se revirtieron los cambios.",
            )

        assistant_turn = ConversationTurn(
            role="assistant",
            content=f"Error: {result.error or 'unknown'}",
            tool_result={"state": "failed", "error": result.error},
        )
        self.conversation_service.add_turn(session_id, assistant_turn)
        return self.response_composer.compose_error(
            result.error or "Ocurrió un error al ejecutar el plan.",
        )

    def _record_trace(
        self, session_id: str, intent: ParsedIntent, context: ContextSnapshot,
        tools: list[str], result_codes: list[str],
        correlation_id: str, start: datetime,
        provider: str = "rules",
    ) -> None:
        try:
            duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            trace = AssistantTrace(
                trace_id=uuid.uuid4().hex[:16],
                session_id=session_id,
                request_id=correlation_id,
                intent=intent.intent_id,
                provider=provider,
                tools=tuple(tools),
                durations={"total": duration_ms},
                result_codes=tuple(result_codes),
                timestamp=start.isoformat(),
            )
            self.trace_recorder.record(trace)
        except Exception as e:
            logger.debug("Trace recording failed: %s", e)

    def _build_provider_messages(self, session_id: str, text: str) -> list[dict[str, str]]:
        context_messages = self.conversation_service.get_context_messages(session_id)
        context_messages.append({"role": "user", "content": text})
        return context_messages

    def shutdown(self) -> None:
        self._initialized = False
