from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from michi_ai.v2 import AssistantCoreService
from michi_ai.v2.context.context_assembler import ContextAssembler
from michi_ai.v2.conversation.conversation_service import ConversationService
from michi_ai.v2.core.response_composer import ResponseComposer
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.intent.intent_router_v2 import IntentRouterV2
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.provider.provider_router import ProviderRouter
from michi_ai.v2.suggest.suggestion_engine_v2 import SuggestionEngineV2
from michi_ai.v2.tools.register_builtin import (
    AssistantGateways, register_builtin_tools,
)
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
from michi_ai.v2.trace.trace_recorder import TraceRecorder

from core.assistant_gateways import (
    ProductionAudioLabGateway, ProductionDeviceGateway,
    ProductionDiagnosticsGateway, ProductionJobGateway,
    ProductionLibraryGateway, ProductionMixGateway,
    ProductionNavigationGateway, ProductionPlaybackGateway,
    ProductionSettingsGateway, UnavailableRadioGateway,
    ProductionPlaylistServiceGateway, ProductionQueueServiceGateway,
)
from core.assistant_metadata_gateway import ProductionMetadataGateway
from core.assistant_context_providers import register_all_context_providers

logger = logging.getLogger(__name__)


def _make_gateway(gateway_class_name: str, service: Any) -> Any:
    if service is None:
        return None
    from michi_ai.v2.tools.tool_definitions import (
        CONNECTIONS_GATEWAY, HOME_AUDIO_GATEWAY, LYRICS_GATEWAY,
        LIBRARY_DOCTOR_GATEWAY,
    )
    mapping = {
        "LyricsGateway": LYRICS_GATEWAY,
        "LibraryDoctorGateway": LIBRARY_DOCTOR_GATEWAY,
        "ConnectionsGateway": CONNECTIONS_GATEWAY,
        "HomeAudioGateway": HOME_AUDIO_GATEWAY,
    }
    cls = mapping.get(gateway_class_name)
    if cls is None:
        return None
    return cls(service)


@dataclass(frozen=True)
class AssistantComposition:
    core_service: AssistantCoreService
    tool_registry: ToolRegistryV2
    capability_resolver: CapabilityResolver
    context_assembler: ContextAssembler
    conversation_service: ConversationService
    confirmation_policy: ConfirmationPolicyV2
    trace_recorder: TraceRecorder
    gateways: AssistantGateways


def create_assistant_composition(
    metadata_service: Any = None,
    queue_service: Any = None,
    playlist_service: Any = None,
    confirmation_service: Any = None,
    job_service: Any = None,
    settings_service: Any = None,
    player_service: Any = None,
    library_db: Any = None,
    audio_lab_service: Any = None,
    sync_manager: Any = None,
    diagnostics_service: Any = None,
    mix_service: Any = None,
    navigation_service: Any = None,
    lyrics_service: Any = None,
    connection_service: Any = None,
    home_audio_service: Any = None,
) -> AssistantComposition:
    tool_registry = ToolRegistryV2()
    capability_resolver = CapabilityResolver()
    context_assembler = ContextAssembler()
    conversation_service = ConversationService()
    confirmation_policy = ConfirmationPolicyV2()
    plan_executor = PlanExecutorV2(tool_registry)
    plan_validator = PlanValidator(tool_registry, capability_resolver)
    plan_builder = PlanBuilderV2(tool_registry, capability_resolver)

    gateways = AssistantGateways(
        playback=ProductionPlaybackGateway(player_service),
        queue=ProductionQueueServiceGateway(queue_service or player_service),
        library=ProductionLibraryGateway(library_db),
        playlists=ProductionPlaylistServiceGateway(playlist_service or library_db),
        settings=ProductionSettingsGateway(settings_service),
        audio_lab=ProductionAudioLabGateway(audio_lab_service),
        devices=ProductionDeviceGateway(sync_manager),
        diagnostics=ProductionDiagnosticsGateway(diagnostics_service),
        mix=ProductionMixGateway(mix_service),
        jobs=ProductionJobGateway(job_service),
        navigation=ProductionNavigationGateway(navigation_service),
        radio=UnavailableRadioGateway(),
        metadata=ProductionMetadataGateway(
            metadata_service=metadata_service,
            confirmation_service=confirmation_service,
            job_service=job_service,
        ) if metadata_service else None,
        lyrics=_make_gateway("LyricsGateway", lyrics_service),
        library_doctor=_make_gateway("LibraryDoctorGateway", diagnostics_service),
        connections=_make_gateway("ConnectionsGateway", connection_service),
        home_audio=_make_gateway("HomeAudioGateway", home_audio_service),
    )

    register_builtin_tools(tool_registry, gateways, capabilities=capability_resolver)
    core = AssistantCoreService(
        intent_router=IntentRouterV2(),
        context_assembler=context_assembler,
        tool_registry=tool_registry,
        capability_resolver=capability_resolver,
        plan_builder=plan_builder,
        plan_validator=plan_validator,
        plan_executor=plan_executor,
        confirmation_policy=confirmation_policy,
        provider_router=ProviderRouter(),
        conversation_service=conversation_service,
        suggestion_engine=SuggestionEngineV2(),
        trace_recorder=TraceRecorder(),
        response_composer=ResponseComposer(),
    )
    core.register_gateways(gateways.to_dict())

    svc_map = {
        "player_service": player_service,
        "library_db": library_db,
        "settings_service": settings_service,
        "job_service": job_service,
        "sync_manager": sync_manager,
        "diagnostics_service": diagnostics_service,
        "navigation_bridge": navigation_bridge,
    }
    register_all_context_providers(context_assembler, svc_map)
    core.initialize()

    return AssistantComposition(
        core_service=core,
        tool_registry=tool_registry,
        capability_resolver=capability_resolver,
        context_assembler=context_assembler,
        conversation_service=conversation_service,
        confirmation_policy=confirmation_policy,
        trace_recorder=core.trace_recorder,
        gateways=gateways,
    )
