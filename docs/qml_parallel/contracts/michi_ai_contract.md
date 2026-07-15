<<<<<<< Updated upstream
<<<<<<< Updated upstream
# MichiAIBridge Integration Contract
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
# Michi AI Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `michiAIBridge` / `aiBridge` → `MichiAIBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `status` | `str` | `statusChanged` |
| `lastError` | `str` | `contextChanged` |
| `suggestions` | `QVariantList` | `contextChanged` |

Suggestion schema: `{title: str, description: str, action: str, route: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `cancel` | (none) | none |
| `sendMessage` | (none) | `text: str` |
| `getChatHistory` | `str` (JSON) | none |
| `aiScore` | `dict` | none |

## Signals
| Signal | Payload |
|---|---|
| `contextChanged` | (none) |
| `responseReceived` | `response: str` |
| `statusChanged` | `new_status: str` |

## Models Exposed
None. Chat history exposed as JSON string via `getChatHistory()` slot.

## Error Types/Codes
- `"NO_SEARCH_SERVICE"` — global search not injected
- `"NO_TRACK_ACTION_SERVICE"` / `"NO_TRACK_ACTION_SERVICE"` — TrackActionService missing
- `"TRACK_NOT_FOUND"` — search returned no tracks
- `"NO_ENQUEUE_METHOD"` — enqueue_track not available on TAS
- `"SIN_QUERY"` — blank search query
- `"NO_NAVIGATION_SERVICE"` — NavigationBridge missing
- `"NO_PLAYLIST_SERVICE"` — no playlist service
- `"NO_CREATE_METHOD"` — create method not available
- `"NO_PLAYLIST_ID"` — playlist ID not found in text
- `"NO_DIAGNOSTICS_SERVICE"` — diagnostics service missing
- `"NO_SETTINGS_SERVICE"` — settings service missing
- Error codes from `_dispatch_action` fallthrough

## Valid States
`"idle"`, `"understanding"`, `"planning"`, `"awaiting_confirmation"`, `"executing"`, `"completed"`, `"cancelled"`, `"failed"`.

## Lifecycle Expectations
- Constructor takes optional: `ai_controller`, `context_service`, `plan_builder`, `tool_registry`, `action_registry`, `navigation_bridge`, `track_action_service`, `playlist_service`, `global_search_service`, `settings_service`, `diagnostics_service`, `worker_manager`.
- `refresh()` builds suggestions from `ContextService.get_suggestions()` or returns 5 static defaults.
- `sendMessage(text)` resolves user intent via pattern matching in Spanish.
- Chat history is stored in-memory as list of `{role, text}` dicts (no persistence).
- `status` transitions through valid states via `_set_status()`.

## Behavior When Service Is Missing/Null
Most services gracefully degrade — individual `_action_*` methods check and return appropriate error codes.

## Destructive Actions and Confirmations
The following actions require `requires_confirmation=True`:
- Creating a playlist (`crear playlist`)
- Adding songs to a playlist (`agregar canciones`)
- Changing a setting (`cambiar ajuste seguro`)

When confirmation required:
1. State transitions to `"awaiting_confirmation"`
2. Response asks "¿Confirmas que quieres...?"
3. User replies "sí"/"confirmar"/"yes" to confirm → `_execute_action` called
4. User replies "no"/"cancelar"/"cancel" to reject → status `"cancelled"`

## Cancellation Contract
- `cancel()`: cancels task via `_wm.cancel_task(_current_task_id)` if WorkerManager available. Clears `_pending_action` and `_last_error`. Sets status to `"cancelled"`.
- User saying "no"/"cancelar"/"cancel" during `awaiting_confirmation`: sets `_pending_action = None`, status `"cancelled"`, sends "Acción cancelada." response.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- Actions requiring confirmation: `crear playlist`, `agregar canciones`, `cambiar ajuste seguro`
- Confirmation flow: user sends message → bridge responds with "¿Confirmas?" → user says sí/no
- `_pending_action` stores the action awaiting confirmation
- `_resolve_action` intercepts "sí"/"no" to confirm or cancel pending action
=======
# MichiAIBridge Integration Contract

## Context Property
- `michiAIBridge` / `aiBridge` → `MichiAIBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `status` | `str` | `statusChanged` |
| `lastError` | `str` | `contextChanged` |
| `suggestions` | `QVariantList` | `contextChanged` |

Suggestion schema: `{title: str, description: str, action: str, route: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `cancel` | (none) | none |
| `sendMessage` | (none) | `text: str` |
| `getChatHistory` | `str` (JSON) | none |
| `aiScore` | `dict` | none |

## Signals
| Signal | Payload |
|---|---|
| `contextChanged` | (none) |
| `responseReceived` | `response: str` |
| `statusChanged` | `new_status: str` |

## Models Exposed
None. Chat history exposed as JSON string via `getChatHistory()` slot.

## Error Types/Codes
- `"NO_SEARCH_SERVICE"` — global search not injected
- `"NO_TRACK_ACTION_SERVICE"` / `"NO_TRACK_ACTION_SERVICE"` — TrackActionService missing
- `"TRACK_NOT_FOUND"` — search returned no tracks
- `"NO_ENQUEUE_METHOD"` — enqueue_track not available on TAS
- `"SIN_QUERY"` — blank search query
- `"NO_NAVIGATION_SERVICE"` — NavigationBridge missing
- `"NO_PLAYLIST_SERVICE"` — no playlist service
- `"NO_CREATE_METHOD"` — create method not available
- `"NO_PLAYLIST_ID"` — playlist ID not found in text
- `"NO_DIAGNOSTICS_SERVICE"` — diagnostics service missing
- `"NO_SETTINGS_SERVICE"` — settings service missing
- Error codes from `_dispatch_action` fallthrough

## Valid States
`"idle"`, `"understanding"`, `"planning"`, `"awaiting_confirmation"`, `"executing"`, `"completed"`, `"cancelled"`, `"failed"`.

## Lifecycle Expectations
- Constructor takes optional: `ai_controller`, `context_service`, `plan_builder`, `tool_registry`, `action_registry`, `navigation_bridge`, `track_action_service`, `playlist_service`, `global_search_service`, `settings_service`, `diagnostics_service`, `worker_manager`.
- `refresh()` builds suggestions from `ContextService.get_suggestions()` or returns 5 static defaults.
- `sendMessage(text)` resolves user intent via pattern matching in Spanish.
- Chat history is stored in-memory as list of `{role, text}` dicts (no persistence).
- `status` transitions through valid states via `_set_status()`.

## Behavior When Service Is Missing/Null
Most services gracefully degrade — individual `_action_*` methods check and return appropriate error codes.

## Destructive Actions and Confirmations
The following actions require `requires_confirmation=True`:
- Creating a playlist (`crear playlist`)
- Adding songs to a playlist (`agregar canciones`)
- Changing a setting (`cambiar ajuste seguro`)

When confirmation required:
1. State transitions to `"awaiting_confirmation"`
2. Response asks "¿Confirmas que quieres...?"
3. User replies "sí"/"confirmar"/"yes" to confirm → `_execute_action` called
4. User replies "no"/"cancelar"/"cancel" to reject → status `"cancelled"`

## Cancellation Contract
- `cancel()`: cancels task via `_wm.cancel_task(_current_task_id)` if WorkerManager available. Clears `_pending_action` and `_last_error`. Sets status to `"cancelled"`.
- User saying "no"/"cancelar"/"cancel" during `awaiting_confirmation`: sets `_pending_action = None`, status `"cancelled"`, sends "Acción cancelada." response.

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
## Integration with JobService
- Uses `WorkerManager` (`_wm`) via `cancel_task` for cancellation.
- NOT using JobBridge — direct WorkerManager integration.

## Integration with ActionRegistry
- `_dispatch_action` delegates `"abrir ajustes"` to `NavigationBridge.navigate("settings")`.
- `_action_change_setting` uses `SettingsService.set_()` to change settings.
- ActionRegistry passed as constructor dependency but not directly used in current code.

## Integration with NavigationBridge
- `_action_open_route()`: maps Spanish keywords to routes (`biblioteca`→`library`, `inicio`→`home`, etc.) and calls `_nav.navigate(target)`.
- `_execute_action("abrir ajustes")`: calls `_nav.navigate("settings")`.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.

## Recognized Intents (Spanish)
`reproducir canción`, `reproducir álbum`, `encolar`, `buscar`, `abrir ruta`, `crear playlist`, `agregar canciones`, `mostrar no escuchadas`, `diagnosticar biblioteca`, `abrir ajustes`, `cambiar ajuste seguro`.
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
