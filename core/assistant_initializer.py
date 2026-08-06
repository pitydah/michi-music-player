"""Build the dependency composition for the Michi assistant runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from michi_ai.v2.context.context_assembler import ContextAssembler
from michi_ai.v2.conversation.conversation_service import ConversationService
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.tools.register_builtin import register_builtin_tools
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2
from michi_ai.v2.trace.trace_recorder import TraceRecorder

from core.assistant_gateways import (
    AssistantGateways,
    ProductionAudioLabGateway, ProductionDeviceGateway,
    ProductionDiagnosticsGateway, ProductionJobGateway,
    ProductionLibraryGateway, ProductionLibraryDoctorGateway,
    ProductionMixGateway, ProductionNavigationGateway,
    ProductionPlaybackGateway, ProductionSettingsGateway,
    UnavailableRadioGateway,
    ProductionPlaylistGateway, ProductionQueueGateway,
)
from core.assistant_metadata_gateway import ProductionMetadataGateway
from core.assistant_context_providers import register_all_context_providers

logger = logging.getLogger(__name__)


def _make_gateway(gateway_class_name: str, service: Any) -> Any:
    if service is None:
        return None
    mapping: dict[str, type] = {}
    try:
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
    except ImportError:
        pass
    cls = mapping.get(gateway_class_name)
    if cls is None:
        return None
    return cls(service)


@dataclass(frozen=True)
class AssistantComposition:
    core_service: Any  # AssistantCoreService or MichiAIEngine
    tool_registry: ToolRegistryV2
    capability_resolver: CapabilityResolver
    planner: PlanBuilderV2
    validator: PlanValidator
    executor: PlanExecutorV2
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
    library_doctor_service: Any = None,
    track_action_service: Any = None,
    library_query_service: Any = None,
    device_registry: Any = None,
    global_search_service: Any = None,
    metadata_editor_service: Any = None,
) -> AssistantComposition:
    """Compose the assistant engine, gateways, tools, and context providers.

    Args:
        metadata_service, confirmation_service: Services for metadata operations and
            their confirmation flow.
        queue_service, playlist_service, track_action_service, library_query_service:
            Playback collection and track-operation services injected into gateways.
        player_service, library_db, settings_service: Core playback, library, and
            settings dependencies.
        job_service, sync_manager, diagnostics_service, navigation_service: Runtime
            infrastructure used by gateways and context providers.
        audio_lab_service, mix_service: Audio analysis and mix services.
        lyrics_service, connection_service, home_audio_service,
            library_doctor_service: Optional capability-specific services.

    Returns:
        The fully wired assistant composition.
    """
    from core.ai_engine import MichiAIEngine
    from core.ai.backend_selector import BackendSelector
    from core.ai.model_manager import ModelManager

    # ONE CapabilityResolver instance is shared across the registry (via
    # register_builtin_tools), the planner, the validator, and the executor.
    # The ToolRegistryV2 is constructed WITH that resolver so that
    # execution-time capability checks (ToolRegistryV2.execute) reflect
    # gateway evidence, not merely handler existence.
    capability_resolver = CapabilityResolver()
    tool_registry = ToolRegistryV2(capability_resolver=capability_resolver)
    context_assembler = ContextAssembler()
    conversation_service = ConversationService()
    confirmation_policy = ConfirmationPolicyV2()
    executor = PlanExecutorV2(tool_registry)
    validator = PlanValidator(tool_registry, capability_resolver)
    planner = PlanBuilderV2(tool_registry, capability_resolver)
    trace_recorder = TraceRecorder()

    # Gateways are constructed ONLY when at least one backing service exists;
    # an unbacked gateway is omitted so its capabilities are never advertised.
    gateways = AssistantGateways(
        playback=(ProductionPlaybackGateway(
            player_service, queue_service, track_action_service,
            playlist_service, library_query_service)
            if (player_service or queue_service or track_action_service
                or playlist_service or library_query_service) else None),
        queue=(ProductionQueueGateway(queue_service, library_query_service)
               if (queue_service or library_query_service) else None),
        library=(ProductionLibraryGateway(library_db, library_query_service,
                                          global_search_service)
                 if (library_db or library_query_service
                     or global_search_service) else None),
        playlists=(ProductionPlaylistGateway(library_db, playlist_service)
                   if (library_db or playlist_service) else None),
        settings=ProductionSettingsGateway(settings_service) if settings_service else None,
        audio_lab=(ProductionAudioLabGateway(audio_lab_service, library_db)
                   if audio_lab_service else None),
        devices=(ProductionDeviceGateway(
            sync_manager, connection_service, device_registry, home_audio_service)
            if (sync_manager or connection_service) else None),
        diagnostics=ProductionDiagnosticsGateway(diagnostics_service) if diagnostics_service else None,
        mix=(ProductionMixGateway(mix_service, playlist_service, job_service)
             if mix_service else None),
        jobs=ProductionJobGateway(job_service) if job_service else None,
        navigation=ProductionNavigationGateway(navigation_service) if navigation_service else None,
        radio=UnavailableRadioGateway(),
        metadata=ProductionMetadataGateway(
            metadata_service=metadata_service,
            confirmation_service=confirmation_service,
            job_service=job_service,
            metadata_editor=metadata_editor_service,
        ) if (metadata_service or metadata_editor_service) else None,
        lyrics=_make_gateway("LyricsGateway", lyrics_service),
        library_doctor=(ProductionLibraryDoctorGateway(
            library_doctor_service, job_service, library_db)
            if library_doctor_service else None),
        connections=_make_gateway("ConnectionsGateway", connection_service),
        home_audio=_make_gateway("HomeAudioGateway", home_audio_service),
    )

    register_builtin_tools(tool_registry, gateways, capabilities=capability_resolver)

    model_manager = ModelManager()
    backend_selector = BackendSelector(model_manager=model_manager)
    engine = MichiAIEngine(
        tool_registry=tool_registry,
        backend_selector=backend_selector,
    )

    svc_map = {
        "player_service": player_service,
        "queue_service": queue_service,
        "library_db": library_db,
        "settings_service": settings_service,
        "job_service": job_service,
        "sync_manager": sync_manager,
        "diagnostics_service": diagnostics_service,
        "navigation_service": navigation_service,
    }
    register_all_context_providers(context_assembler, svc_map)

    return AssistantComposition(
        core_service=engine,
        tool_registry=tool_registry,
        capability_resolver=capability_resolver,
        planner=planner,
        validator=validator,
        executor=executor,
        context_assembler=context_assembler,
        conversation_service=conversation_service,
        confirmation_policy=confirmation_policy,
        trace_recorder=trace_recorder,
        gateways=gateways,
    )
