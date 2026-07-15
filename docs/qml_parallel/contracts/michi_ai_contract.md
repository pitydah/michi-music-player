# Michi AI Bridge Contract

## Context Property
`MichiAIBridge` registered as `michi_ai` context property.

## Class Name
`MichiAIBridge` (`ui_qml_bridge/michi_ai_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `ai_controller` | `AIController \| None` | `None` |
| `context_service` | `ContextService \| None` | `None` |
| `plan_builder` | `PlanBuilder \| None` | `None` |
| `tool_registry` | `ToolRegistry \| None` | `None` |
| `action_registry` | `ActionRegistry \| None` | `None` |
| `navigation_bridge` | `NavigationBridge \| None` | `None` |
| `track_action_service` | `Any \| None` | `None` |
| `playlist_service` | `Any \| None` | `None` |
| `global_search_service` | `Any \| None` | `None` |
| `settings_service` | `Any \| None` | `None` |
| `diagnostics_service` | `Any \| None` | `None` |
| `worker_manager` | `WorkerManager \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `status` | `str` | `statusChanged` | Current state: idle/understanding/planning/awaiting_confirmation/executing/completed/cancelled/failed |
| `lastError` | `str` | `contextChanged` | Last error message |
| `suggestions` | `QVariantList` | `contextChanged` | Contextual suggestions (max 5) with title, description, action, route |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `void` | Rebuild suggestions from context service |
| `cancel` | — | `void` | Cancel current task; reset to cancelled state |
| `sendMessage` | `text: str` | `void` | Process natural language input; route to action or await confirmation |
| `getChatHistory` | — | `str` | Return JSON string of chat history |
| `aiScore` | — | `dict` | Return capability score (0-100) with sub-metrics |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `contextChanged` | — | Suggestions, chat history, or error changed |
| `responseReceived` | `str` | Assistant response text emitted |
| `statusChanged` | `str` | State machine transitioned |

## Models Exposed
None. Chat history returned as JSON string.

## VALID_STATES
idle, understanding, planning, awaiting_confirmation, executing, completed, cancelled, failed

## Error Handling
- Internal error codes used in response text (not dict returns)
- `_dispatch_action` returns dict; failures are converted to chat responses
- Error in response: `"Error al <description>: <error message>"`
- All exceptions caught per action dispatch

## Recognized Actions (10)
| Action | Requires Confirmation | Description |
|--------|----------------------|-------------|
| `reproducir canción` | No | Play a track by name or ID |
| `reproducir álbum` | No | Play an album |
| `encolar` | No | Enqueue tracks |
| `buscar` | No | Search library |
| `abrir ruta` | No | Navigate to section |
| `crear playlist` | Yes | Create new playlist |
| `agregar canciones` | Yes | Add songs to playlist |
| `mostrar no escuchadas` | No | Show unplayed tracks |
| `diagnosticar biblioteca` | No | Run quick diagnostics |
| `abrir ajustes` | No | Navigate to settings |

## States
| State | Meaning |
|-------|---------|
| `idle` | No active conversation |
| `understanding` | Processing user message |
| `planning` | Building execution plan |
| `awaiting_confirmation` | Waiting for user yes/no on destructive action |
| `executing` | Dispatching action to service |
| `completed` | Action succeeded |
| `cancelled` | User cancelled or system cancelled |
| `failed` | Action execution failed |

## Lifecycle
- Created by `BridgeFactory.create_michi_ai_bridge()` — attempts to create AIController, ContextService, PlanBuilder, ToolRegistry internally, silently catching import failures
- No auto-refresh; `refresh()` must be called to populate suggestions
- Chat history stored in-memory as list of dicts

## Behavior When Service Is Null/Missing
- Without `context_service`: fallback hardcoded suggestions shown (5 default items)
- Without `track_action_service`: play/enqueue operations return error
- Without `global_search_service`: search operations fail
- Without `playlist_service`: playlist creation/delegation fails
- Without `navigation_bridge`: route navigation fails
- Without `diagnostics_service`: diagnostic action fails
- Without `settings_service`: setting changes fail
- Without `worker_manager`: task cancellation no-op

## Integration
- **JobService**: Uses `worker_manager` for task cancellation
- **ActionRegistry**: Not directly used in action dispatch
- **NavigationBridge**: Used for `abrir ruta` and `abrir ajustes` actions
- **CapabilityBridge**: Registered as `michi_ai` bridge with no explicit capability gate; `aiScore` checks all dependencies

## Cancellation Contract
- `cancel()` cancels task via `_wm.cancel_task(task_id)` and resets state to "cancelled"
- `_pending_action` cleared on cancel
- No generation counter; single pending action at a time

## Destructive Action Handling
- Actions requiring confirmation: `crear playlist`, `agregar canciones`, `cambiar ajuste seguro`
- Confirmation flow: user sends message → bridge responds with "¿Confirmas?" → user says sí/no
- `_pending_action` stores the action awaiting confirmation
- `_resolve_action` intercepts "sí"/"no" to confirm or cancel pending action
