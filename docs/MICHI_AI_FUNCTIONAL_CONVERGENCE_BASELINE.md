# Michi AI Functional Convergence Baseline

| Field | Value |
|-------|-------|
| Branch | `integration/michi-ai-functional-convergence-v2` |
| SHA | `004a189` |
| Base | `origin/integration/core-services-convergence-v1` |
| Date | 2026-07-14 |

## Existing Components

| Component | Location | Status |
|-----------|----------|--------|
| AssistantCoreService | `michi_ai/v2/core/assistant_core.py` | ✅ |
| ToolRegistryV2 | `michi_ai/v2/tools/tool_registry_v2.py` | ✅ |
| CapabilityResolver | `michi_ai/v2/intent/capability_resolver.py` | ✅ |
| ContextAssembler | `michi_ai/v2/context/context_assembler.py` | ✅ |
| PlanBuilderV2 | `michi_ai/v2/plan/plan_builder_v2.py` | ✅ |
| PlanValidator | `michi_ai/v2/plan/plan_validator.py` | ✅ |
| PlanExecutorV2 | `michi_ai/v2/plan/plan_executor_v2.py` | ✅ |
| ConfirmationPolicyV2 | `michi_ai/v2/plan/confirmation_policy_v2.py` | ✅ |
| ProviderRouter | `michi_ai/v2/provider/provider_router.py` | ✅ |
| ConversationService | `michi_ai/v2/conversation/conversation_service.py` | ✅ |
| SuggestionEngineV2 | `michi_ai/v2/suggest/suggestion_engine_v2.py` | ✅ |
| TraceRecorder | `michi_ai/v2/trace/trace_recorder.py` | ✅ |
| ResponseComposer | `michi_ai/v2/core/response_composer.py` | ✅ |
| AssistantGateways | `core/assistant_gateways.py` | ✅ (needs fixes) |
| ContextProviders | `core/assistant_context_providers.py` | ✅ (needs Metadata provider) |
| ServiceContainer | `core/service_container.py` | ✅ |
| ServiceBundle | `ui_qml_bridge/service_bundle.py` | ✅ |
| BridgeFactory | `ui_qml_bridge/bridge_factory.py` | ✅ (clean) |
| MichiAIBridge | `ui_qml_bridge/michi_ai_bridge.py` | ✅ (thin, sync) |
| Metadata legacy | `metadata/` | ✅ (tag_reader, tag_writer, review services) |
| Production gateways | `core/assistant_gateways.py` | ⚠️ needs fixes |
| Async execution | NOT YET | ❌ |
| ProductionMetadataGateway | NOT YET | ❌ |
| Dynamic capabilities | NOT YET | ❌ |

## Key Issues Found

1. `AssistantGateways.to_dict()` does not export all 17 gateway fields
2. `assistant_initializer.py` does not exist — assistant built inside `ServiceContainer`
3. `BridgeFactory.create_michi_ai_bridge()` still calls `registry.ensure_assistant_core()`
4. `ProductionQueueGateway` uses `PlayerService` instead of `QueueService`
5. `ProductionPlaylistGateway` uses `LibraryQueryService` instead of `PlaylistService`
6. `set_shuffle()` uses toggle without state comparison
7. No async execution — `sendMessage()` blocks QML thread
8. No dynamic capability states
9. No MetadataGateway
10. No metadata context provider
