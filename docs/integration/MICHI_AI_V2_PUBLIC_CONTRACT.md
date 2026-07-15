# Michi AI V2 — Public Integration Contract

**Version:** 2.0.0  
**Branch:** michi-ai-functional-v2  
**Status:** FROZEN — no breaking changes without review

---

## Constructor

```python
from michi_ai.v2.core.assistant_core import AssistantCoreService

core = AssistantCoreService(
    intent_router=None,        # Optional IntentRouterV2
    context_assembler=None,    # Optional ContextAssembler
    tool_registry=None,        # Optional ToolRegistryV2
    capability_resolver=None,  # Optional CapabilityResolver
    plan_builder=None,         # Optional PlanBuilderV2
    plan_validator=None,       # Optional PlanValidator
    plan_executor=None,        # Optional PlanExecutorV2
    confirmation_policy=None,  # Optional ConfirmationPolicyV2
    provider_router=None,      # Optional ProviderRouter
    conversation_service=None, # Optional ConversationService
    suggestion_engine=None,    # Optional SuggestionEngineV2
    trace_recorder=None,       # Optional TraceRecorder
    response_composer=None,    # Optional ResponseComposer
)
```

All parameters optional — defaults provided.

---

## Signals / Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `plan_executor.on_progress` | Step completed | `(plan_id, state, current, total)` |
| `plan_executor.on_complete` | Plan finished | `PlanExecution` |

---

## Public Methods

### `register_gateway(name, gateway)`
Register a gateway for tools (playback, queue, library, playlist, etc.).

### `register_gateways(gateways: dict)`
Bulk register gateways.

### `initialize() -> OperationResult`
Initialize capabilities from gateways.

### `process_message(request: AssistantRequest) -> AssistantResponse`
Process a user message end-to-end.

### `confirm_plan(confirmation_id, session_id) -> AssistantResponse`
Confirm a pending plan for execution.

### `cancel_plan(session_id) -> AssistantResponse`
Cancel a pending plan.

### `cancel_execution(plan_id) -> bool`
Cancel a running execution.

### `get_suggestions(session_id) -> list[Suggestion]`
Get contextual suggestions.

### `dismiss_suggestion(suggestion_id) -> bool`
Dismiss a suggestion.

### `get_session(session_id) -> OperationResult[AssistantSession]`
Get or validate a session.

### `create_session() -> OperationResult[AssistantSession]`
Create a new session.

### `clear_history(session_id) -> OperationResult`
Clear conversation history.

### `get_tools() -> list[ToolDefinition]`
Get registered tool definitions.

---

## Request/Response Shapes

### AssistantRequest
- `text: str` — user input
- `session_id: str` — session identifier
- `context_snapshot_id: str` — (optional) context reference
- `allowed_capabilities: tuple[str, ...]` — permitted capabilities
- `correlation_id: str` — request tracing

### AssistantResponse
- `type: AssistantResponseType` — ANSWER, CLARIFICATION, PLAN_PREVIEW, CONFIRMATION_REQUEST, EXECUTION_PROGRESS, EXECUTION_RESULT, ERROR, SUGGESTION
- `title: str` — response title
- `message: str` — response body
- `details: str` — additional details
- `actions: tuple[dict]` — action suggestions
- `plan: ActionPlan | None` — associated plan
- `progress: dict | None` — execution progress
- `error: str` — error message
- `trace_id: str` — trace identifier
- `correlation_id: str` — correlation identifier

### OperationResult[T]
- `ok: bool`
- `code: ErrorCode`
- `message: str`
- `data: T | None`
- `warnings: tuple[str, ...]`
- `errors: tuple[str, ...]`
- `requires_confirmation: bool`
- `retryable: bool`
- `cancelled: bool`
- `correlation_id: str`

---

## Error Codes

| Code | Meaning |
|------|---------|
| `OK` | Success |
| `NO_MATCH` | No intent matched |
| `AMBIGUOUS_INTENT` | Multiple intents with similar confidence |
| `INVALID_ARGUMENTS` | Tool argument validation failed |
| `CAPABILITY_UNAVAILABLE` | Required capability not registered or unavailable |
| `TOOL_NOT_FOUND` | Tool name not in registry |
| `TOOL_UNAVAILABLE` | Tool registered but no handler |
| `TOOL_TIMEOUT` | Tool execution exceeded timeout |
| `TOOL_CANCELLED` | Tool execution cancelled |
| `TOOL_FAILED` | Tool execution failed |
| `CONFIRMATION_REQUIRED` | Action requires user confirmation |
| `CONFIRMATION_EXPIRED` | Confirmation request expired or consumed |
| `PLAN_INVALID` | Plan validation failed |
| `PLAN_STEP_FAILED` | A plan step failed |
| `PLAN_CANCELLED` | Plan cancelled by user |
| `ROLLBACK_SUCCEEDED` | Rollback completed |
| `ROLLBACK_FAILED` | Rollback failed |
| `PROVIDER_UNAVAILABLE` | AI provider not reachable |
| `PROVIDER_TIMEOUT` | AI provider timed out |
| `PROVIDER_INVALID_RESPONSE` | AI provider returned invalid data |
| `CONTEXT_REJECTED` | Context assembly rejected |
| `PRIVACY_BLOCKED` | Privacy policy blocked access |
| `SESSION_NOT_FOUND` | Session does not exist |
| `INTERNAL_ERROR` | Unexpected internal error |

---

## Required Gateways

Each gateway is a Protocol (runtime_checkable) in `michi_ai/v2/core/gateways.py`:

| Gateway | Protocol | Methods |
|---------|----------|---------|
| `playback` | `PlaybackGateway` | play_track, play_album, play_artist, play_playlist, pause, resume, stop, next, previous, seek, set_volume, set_repeat, set_shuffle, get_state |
| `queue` | `QueueGateway` | get_queue, add_to_queue, play_next, replace_queue, remove_from_queue, clear_queue, reorder_queue |
| `library` | `LibraryGateway` | search, get_track, get_album, get_artist, list_recent, list_unplayed, list_favorites, find_metadata_gaps |
| `playlist` | `PlaylistGateway` | list_playlists, get_playlist, create_playlist, add_to_playlist, remove_from_playlist, reorder_playlist |
| `audio_lab` | `AudioLabGateway` | probe_audio, analyze_audio, recommend_conversion, preview_conversion, start_conversion, cancel_conversion, analyze_replaygain, check_integrity, compare_audio, get_status |
| `device` | `DeviceGateway` | list_devices, diagnose_ecosystem, diagnose_server, diagnose_home_audio, diagnose_pairing, plan_sync, start_sync, cancel_sync |
| `settings` | `SettingsGateway` | get_setting, suggest_change, preview_change, apply_change, list_settings |
| `diagnostics` | `DiagnosticsGateway` | get_diagnostics, get_audio_diagnostics, get_network_diagnostics |
| `navigation` | `NavigationRequestGateway` | request_navigation |
| `mix` | `MixGateway` | create_mix, explain_mix, save_mix_as_playlist, cancel_mix |
| `job` | `JobGateway` | list_jobs, cancel_job, get_job_status |

---

## Confirmation Policy

| Mode | Behavior |
|------|----------|
| `NONE` | No confirmation required |
| `SOFT` | Confirmation for plans with `requires_confirmation=True` |
| `EXPLICIT` | All actions require confirmation |
| `DESTRUCTIVE` | Destructive tools require confirmation |
| `IRREVERSIBLE` | Only irreversible actions (delete_playlist) require confirmation |

---

## Cancellation Propagation

```
conversation → plan → step → tool → gateway → job
```

Each layer propagates via `CancellationToken.check()` which raises `CancellationError`.

---

## Tool Result Contract

All tool handlers (gateway methods) MUST return `dict`:
```python
{"ok": True, ...}  # success
{"ok": False, "error": "reason", "code": "ERROR_CODE"}  # failure
```

NEVER return `{"ok": True}` when gateway returns `None`.
