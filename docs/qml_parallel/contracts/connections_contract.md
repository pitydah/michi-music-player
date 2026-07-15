# ConnectionsBridge Integration Contract

## Context Property
- `connectionsBridge` → `ConnectionsBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `microServerState` | `str` | `stateChanged` |
| `microServerAlias` | `str` | `stateChanged` |
| `microServerContract` | `str` | `stateChanged` |
| `lastError` | `str` | `stateChanged` |
| `latencyMs` | `int` | `stateChanged` |
| `serverVersion` | `str` | `stateChanged` |
| `discoveredServers` | `QVariantList` | `stateChanged` |
| `capabilities` | `QVariantList` | `stateChanged` |
| `lastContact` | `float` | `stateChanged` |

Discovered server schema: `{name: str, host: str, type: str, status: str}`
Capability schema: `{key: str, label: str, enabled: bool}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `scanForServers` | `dict` | none |
| `connectManual` | `dict` | `host: str`, `port: int`, `alias: str` |
| `requestPair` | `dict` | none |
| `confirmPair` | `dict` | none |
| `rejectPair` | `dict` | none |
| `diagnose` | `dict` | none |
| `disconnect` | `dict` | none |
| `forgetServer` | `dict` | none |
| `addManualServer` | `dict` | `host: str = ""`, `port: int = 0`, `alias: str = ""` |
| `reconnect` | `dict` | none |
| `openHomeAudio` | `dict` | `route: str = "home_audio"` |
| `refresh` | `dict` | none |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `stateChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"CANCELLED"` — async operation was cancelled
- `"EMPTY_HOST"` — no host provided for `addManualServer`
- `"UNSUPPORTED"` — reconnect not available in controller
- Exception messages propagated

## States
- `"not_configured"` — initial/after disconnect
- `"scanning"` — actively discovering servers
- `"detected"` — server found (from scan or manual add)
- `"pairing_required"` — pairing requested
- `"paired"` — pairing confirmed (no capabilities yet)
- `"connected"` — fully connected with capabilities
- `"error"` — operation failed

## Contract States
- `"contract_ok"` — `capabilities.contract_ok == True`
- `"contract_partial"` — connected but `contract_ok == False`
- `""` (empty) — not connected

## Lifecycle Expectations
- Constructor takes optional `michi_link_ctrl`, `navigation_bridge`.
- `_cancel_op()` cancels any pending async operation or retry timer.
- `_retry_with_backoff()`: max 3 retries, exponential backoff (1s, 2s, 4s).
- `_update_state()` called by `refresh()` and `diagnose()` to sync from controller capabilities.
- State persisted to QSettings via `core.settings_manager.set_()` for host/port/alias.

## Behavior When Service Is Missing/Null
- No `_ctrl` (MichiLinkController): `_do_scan()` still sets `_state` but may register no servers. `reconnect` returns `UNSUPPORTED`.

## Destructive Actions and Confirmations
- `forgetServer()` — clears saved settings and disconnects. No confirmation required.
- `rejectPair()` — returns to `not_configured`. No confirmation required.

## Cancellation Contract
- `_cancel_op()`: cancels `_async_op` and stops retry timer.
- `_AsyncOp.cancel()`: sets `cancelled = True`; checked in `_do_scan()` after controller call.
- State transitions: scanning → error with `"Cancelado"` message.

## Integration with JobService
NOT IMPLEMENTED.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
- `openHomeAudio(route)`: calls `_nav_bridge.navigate(route)`.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
- MANUALLY EXPOSED via `capabilities` property (static list of 4 keys: `can_continue_playback`, `can_import`, `can_send_genre_playlist`, `can_send_genre_mix`).
- NOT using the shared `CapabilityBridge` — capability state is read from `MichiLinkController.get_capabilities()`.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
