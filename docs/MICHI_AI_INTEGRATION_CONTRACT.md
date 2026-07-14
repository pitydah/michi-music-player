# Michi AI Integration Contract

This document specifies how the QML migration will connect to `AssistantCoreService` via a thin bridge layer.

## Core Service Instantiation (Recommended)

```python
from michi_ai.v2 import AssistantCoreService
from michi_ai.v2.core.assistant_core import IntentRouterV2, ContextAssembler, ToolRegistryV2
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.plan.confirmation_policy_v2 import ConfirmationPolicyV2
from michi_ai.v2.provider.provider_router import ProviderRouter
from michi_ai.v2.conversation.conversation_service import ConversationService
from michi_ai.v2.suggest.suggestion_engine_v2 import SuggestionEngineV2
from michi_ai.v2.trace.trace_recorder import TraceRecorder
from michi_ai.v2.core.response_composer import ResponseComposer
from michi_ai.v2.tools.register_builtin import AssistantGateways, register_builtin_tools

# 1. Create core
tool_registry = ToolRegistryV2()
capability_resolver = CapabilityResolver()

assistant = AssistantCoreService(
    tool_registry=tool_registry,
    capability_resolver=capability_resolver,
    plan_builder=PlanBuilderV2(tool_registry, capability_resolver),
    plan_validator=PlanValidator(tool_registry, capability_resolver),
    plan_executor=PlanExecutorV2(tool_registry),
    # defaults for others
)

# 2. Register gateways (implement the Protocols from gateways.py)
gateways = AssistantGateways(
    playback=my_playback_gateway,   # implements PlaybackGateway
    queue=my_queue_gateway,          # implements QueueGateway
    library=my_library_gateway,      # implements LibraryGateway
    playlist=my_playlist_gateway,    # implements PlaylistGateway
    audio_lab=my_audio_lab_gateway,  # implements AudioLabGateway
    device=my_device_gateway,        # implements DeviceGateway
    settings=my_settings_gateway,    # implements SettingsGateway
    diagnostics=my_diagnostics_gateway, # implements DiagnosticsGateway
    mix=my_mix_gateway,              # implements MixGateway
    navigation=my_nav_gateway,       # implements NavigationRequestGateway
    job=my_job_gateway,              # implements JobGateway
)

# 3. Register all 60 built-in tools
register_builtin_tools(tool_registry, gateways, capabilities=capability_resolver)

# 4. Register gateways with core for context assembly
assistant.register_gateways(gateways.to_dict())

# 5. Initialize
assistant.initialize()
```

## Gateway Registration (alternative using dict)

```python
assistant.register_gateways({
    "playback": playback_gateway,
    "queue": queue_gateway,
    "library": library_gateway,
    "playlist": playlist_gateway,
    "audio_lab": audio_lab_gateway,
    "device": device_gateway,
    "settings": settings_gateway,
    "diagnostics": diagnostics_gateway,
    "navigation": navigation_gateway,
    "mix": mix_gateway,
    "job": job_gateway,
})
```

Each gateway must implement the corresponding protocol from `michi_ai.v2.core.gateways`.

## Bridge API (from QML)

The bridge (`MichiAIBridge`) will surface these operations:

| Method | Returns | Description |
|--------|---------|-------------|
| `processMessage(text, sessionId)` | `dict` (JSON) | Main entry point for user input |
| `confirmPlan(confirmationId, sessionId)` | `dict` | Confirm a pending plan |
| `cancelPlan(sessionId)` | `dict` | Cancel pending plan |
| `cancelExecution(planId)` | `bool` | Cancel running execution |
| `getSuggestions(sessionId)` | `list[dict]` | Get contextual suggestions |
| `dismissSuggestion(suggestionId)` | `bool` | Dismiss a suggestion |
| `getHistory(sessionId, limit)` | `list[dict]` | Get conversation history |
| `clearHistory(sessionId)` | `bool` | Clear conversation history |
| `getTools()` | `list[dict]` | List available tools |

## Response Format (QML-compatible)

All responses are serializable to JSON:

```python
{
    "type": "ANSWER|CLARIFICATION|PLAN_PREVIEW|CONFIRMATION_REQUEST|EXECUTION_PROGRESS|EXECUTION_RESULT|ERROR|SUGGESTION",
    "title": "string",
    "message": "string",
    "details": "string",
    "actions": [...],       # structured action items
    "plan": {...},          # ActionPlan as dict
    "progress": {...},      # execution progress
    "error": "string",
    "trace_id": "string",
    "correlation_id": "string"
}
```

## Context Providers (to register)

The migration layer must register context providers for the `ContextAssembler`:

| Provider Name | Source | Required |
|---------------|--------|----------|
| `playback` | `PlayerService` | Yes |
| `queue` | `QueueService` | No |
| `library` | `LibraryService` | Yes |
| `playlist` | `PlaylistService` | No |
| `navigation` | `NavigationState` | No |
| `devices` | `DeviceService` | No |
| `servers` | `ServerService` | No |
| `settings` | `SettingsManager` | No |
| `jobs` | `JobService` | No |
| `capabilities` | `CapabilityResolver` | No |
| `selection` | `SelectionState` | No |
| `recent_actions` | `HistoryService` | No |

## Files NOT to modify

These files belong to the QML migration layer and must not be changed by AI Core V2:

- `ui_qml_bridge/michi_ai_bridge.py`
- `ui_qml_bridge/action_registry.py`
- `ui_qml_bridge/action_registry_binder.py`
- `ui_qml_bridge/bridge_factory.py`
- `ui_qml_bridge/qml_main.py`
- `ui/**`
- `ui_qml/**`

## Conversation Persistence

| Setting | Default |
|---------|---------|
| Mode | `LOCAL_EPHEMERAL` |
| Path | `~/.local/share/michi/ai_conversations.db` |
| Max turns | 100 |

## Privacy Settings

| Level | Description |
|-------|-------------|
| `MINIMAL` | Only library counts, no paths, no playback |
| `STANDARD` | Strips tokens, passwords, paths |
| `DIAGNOSTIC` | Truncates paths, keeps diagnostic data |
| `LOCAL_FULL` | Full context (only with local provider) |

## Tool Registration

Tools are registered via `register_builtin_tools()` from `michi_ai/v2/tools/register_builtin.py`.
This function registers all 60+ canonical tools with schemas, capabilities, permissions, and handlers.

The migration layer only needs to provide `AssistantGateways` with real gateway implementations.

### Tools requiring confirmation:
- `replace_queue`, `clear_queue`
- `delete_playlist`
- `start_conversion`
- `apply_library_repair`, `rollback_library_repair`
- `start_device_sync`
- `apply_setting_change`, `restore_setting`
- Any tool with `destructive=True`

### Legacy compatibility

An adapter exists at `michi_ai/v2/tools/legacy_adapter.py`:
```python
from michi_ai.v2.tools.legacy_adapter import operation_result_to_legacy
legacy_dict = operation_result_to_legacy(operation_result)
```

This adapter should be removed after full integration.

## Error Codes

See: `michi_ai/v2/core/models.py` — `ErrorCode` enum (25 codes).

## Elements to Eliminate After Integration

| File | Reason |
|------|--------|
| `integrations/ai_assistant/service.py` | Replaced by AssistantCoreService |
| `integrations/ai_assistant/intent_router.py` | Replaced by IntentRouterV2 |
| `integrations/ai_assistant/tool_registry.py` | Replaced by ToolRegistryV2 |
| `integrations/ai_assistant/permissions.py` | Replaced by ToolDefinition |
| `integrations/ai_assistant/schemas.py` | Replaced by v2/core/models.py |
| `integrations/ai_assistant/contextual_suggestion_engine.py` | Replaced by SuggestionEngineV2 |
| `integrations/ai_assistant/conversation_store.py` | Replaced by ConversationService |
| `integrations/ai_assistant/action_confirmation.py` | Replaced by ConfirmationPolicyV2 |
| `integrations/ai_assistant/privacy_guard.py` | Replaced by ContextPrivacyPolicy |
| `integrations/ai_assistant/privacy_filter.py` | Replaced by ContextPrivacyPolicy |
| `integrations/ai_assistant/ollama_client.py` | Replaced by LocalModelProvider |
| `integrations/ai_assistant/tools/*.py` | Replaced by V2 tools via gateways |
| `michi_ai/planner/plan_builder.py` | Replaced by PlanBuilderV2 |
| `michi_ai/planner/plan_executor.py` | Replaced by PlanExecutorV2 |
| `michi_ai/planner/confirmation_policy.py` | Replaced by ConfirmationPolicyV2 |
| `michi_ai/tools/tool_registry.py` | Replaced by ToolRegistryV2 |
| `michi_ai/tools/tool_result.py` | Replaced by OperationResult[T] |
| `michi_ai/context/*.py` | Replaced by ContextAssembler |
| `michi_ai/ui/michi_ai_page.py` | QML will render natively |
