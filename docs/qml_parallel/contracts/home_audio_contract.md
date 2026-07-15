# HomeAudioBridge Integration Contract
# Home Audio Bridge Contract

## Context Property
- `homeAudioBridge` → `HomeAudioBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `homeAssistantAvailable` | `bool` | (constant) |
| `snapcastAvailable` | `bool` | (constant) |
| `receiversAvailable` | `bool` | (constant, always False) |
| `zonesSupported` | `bool` | (constant) |
| `groupingSupported` | `bool` | (constant) |
| `volumeSupported` | `bool` | (constant) |
| `homeAssistantState` | `str` | `stateChanged` |
| `snapcastState` | `str` | `stateChanged` |
| `devices` | `QVariantList` | `stateChanged` |
| `zones` | `QVariantList` | `stateChanged` |
| `receivers` | `QVariantList` | `stateChanged` |
| `lastError` | `str` | `stateChanged` |
| `lastContact` | `float` | `stateChanged` |

Device schema: `{name: str, entity: str}`
Zone schema: `{id: str, name: str, muted: bool, volume: int}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `configureHomeAssistant` | `dict` | `host: str = ""`, `port: int = 0`, `token: str = ""` |
| `testHomeAssistant` | `dict` | none |
| `discoverReceivers` | `dict` | none |
| `openDiagnostics` | `dict` | none |
| `setZoneVolume` | `dict` | `zone_id: str`, `volume: float = 0.5` |
| `setZoneMute` | `dict` | `zone_id: str`, `muted: bool = False` |
| `assignStream` | `dict` | `stream_id: str = ""` |
| `disconnectHa` | `dict` | none |
| `reconnectHa` | `dict` | none |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `stateChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"UNSUPPORTED"` — controller not available
- `"NOT_IMPLEMENTED"` — controller missing method
- `"CONNECTION_FAILED"` — test connection failed
- Exception messages propagated

## States (Home Assistant)
- `"not_configured"` — initial/disconnected
- `"connected"` — connected
- `"error"` — operation failed

## States (Snapcast)
- `"unavailable"` — no Snapcast
- `"available"` — available
- `"error"` — operation failed
- `"concept"` — no Snapcast controller injected at all

## Lifecycle Expectations
- Constructor takes optional `ha_controller`, `snapcast_ctrl`.
- `_retry_with_backoff()`: max 2 retries, exponential backoff (1500ms, 3000ms), cap 10000ms.

## Behavior When Service Is Missing/Null
- No `_ha_ctrl`: `homeAssistantAvailable` = False. `configureHomeAssistant`, `testHomeAssistant` return `UNSUPPORTED`. HA state stays "not_configured".
- No `_snapcast_ctrl` or not available: `snapcastAvailable` = False. Snapcast state set to "concept". Zone operations return `UNSUPPORTED`.
- `receiversAvailable` always False (hardcoded).

## Destructive Actions and Confirmations
None.

## Cancellation Contract
- `_cancel_retry()`: stops retry timer and resets retry count.
- `disconnectHa()`: cancels retry, resets HA state to "not_configured", clears devices.

## Destructive Action Handling
- `disconnectHa()` resets state to not_configured
- No explicit destructive actions; all operations reversible
# HomeAudioBridge Integration Contract

## Context Property
- `homeAudioBridge` → `HomeAudioBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `homeAssistantAvailable` | `bool` | (constant) |
| `snapcastAvailable` | `bool` | (constant) |
| `receiversAvailable` | `bool` | (constant, always False) |
| `zonesSupported` | `bool` | (constant) |
| `groupingSupported` | `bool` | (constant) |
| `volumeSupported` | `bool` | (constant) |
| `homeAssistantState` | `str` | `stateChanged` |
| `snapcastState` | `str` | `stateChanged` |
| `devices` | `QVariantList` | `stateChanged` |
| `zones` | `QVariantList` | `stateChanged` |
| `receivers` | `QVariantList` | `stateChanged` |
| `lastError` | `str` | `stateChanged` |
| `lastContact` | `float` | `stateChanged` |

Device schema: `{name: str, entity: str}`
Zone schema: `{id: str, name: str, muted: bool, volume: int}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `configureHomeAssistant` | `dict` | `host: str = ""`, `port: int = 0`, `token: str = ""` |
| `testHomeAssistant` | `dict` | none |
| `discoverReceivers` | `dict` | none |
| `openDiagnostics` | `dict` | none |
| `setZoneVolume` | `dict` | `zone_id: str`, `volume: float = 0.5` |
| `setZoneMute` | `dict` | `zone_id: str`, `muted: bool = False` |
| `assignStream` | `dict` | `stream_id: str = ""` |
| `disconnectHa` | `dict` | none |
| `reconnectHa` | `dict` | none |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `stateChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"UNSUPPORTED"` — controller not available
- `"NOT_IMPLEMENTED"` — controller missing method
- `"CONNECTION_FAILED"` — test connection failed
- Exception messages propagated

## States (Home Assistant)
- `"not_configured"` — initial/disconnected
- `"connected"` — connected
- `"error"` — operation failed

## States (Snapcast)
- `"unavailable"` — no Snapcast
- `"available"` — available
- `"error"` — operation failed
- `"concept"` — no Snapcast controller injected at all

## Lifecycle Expectations
- Constructor takes optional `ha_controller`, `snapcast_ctrl`.
- `_retry_with_backoff()`: max 2 retries, exponential backoff (1500ms, 3000ms), cap 10000ms.

## Behavior When Service Is Missing/Null
- No `_ha_ctrl`: `homeAssistantAvailable` = False. `configureHomeAssistant`, `testHomeAssistant` return `UNSUPPORTED`. HA state stays "not_configured".
- No `_snapcast_ctrl` or not available: `snapcastAvailable` = False. Snapcast state set to "concept". Zone operations return `UNSUPPORTED`.
- `receiversAvailable` always False (hardcoded).

## Destructive Actions and Confirmations
None.

## Cancellation Contract
- `_cancel_retry()`: stops retry timer and resets retry count.
- `disconnectHa()`: cancels retry, resets HA state to "not_configured", clears devices.

## Integration with JobService
NOT IMPLEMENTED.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
NOT IMPLEMENTED — `openDiagnostics` does not actually navigate to diagnostics.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED — availability is self-detected.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
