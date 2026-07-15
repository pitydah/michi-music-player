# Connections Bridge Contract

## Context Property
`ConnectionsBridge` registered as `connections` context property.

## Class Name
`ConnectionsBridge` (`ui_qml_bridge/connections_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `michi_link_ctrl` | `Any (MichiLinkController) \| None` | `None` |
| `navigation_bridge` | `NavigationBridge \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `microServerState` | `str` | `stateChanged` | Current connection state string |
| `microServerAlias` | `str` | `stateChanged` | Human-readable server alias/name |
| `microServerContract` | `str` | `stateChanged` | Contract status: "contract_ok", "contract_partial", or "" |
| `lastError` | `str` | `stateChanged` | Last error message |
| `latencyMs` | `int` | `stateChanged` | Connection latency in milliseconds |
| `serverVersion` | `str` | `stateChanged` | Server version string |
| `discoveredServers` | `QVariantList` | `stateChanged` | List of discovered servers with name, host, type, status |
| `capabilities` | `QVariantList` | `stateChanged` | List of capability dicts with key, label, enabled |
| `lastContact` | `float` | `stateChanged` | Unix timestamp of last successful contact |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `scanForServers` | — | `dict` | Start server discovery scan |
| `connectManual` | `host: str, port: int, alias: str` | `dict` | Configure manual server connection |
| `requestPair` | — | `dict` | Transition to pairing_required state |
| `confirmPair` | — | `dict` | Confirm pairing; fetch capabilities, set contract status |
| `rejectPair` | — | `dict` | Reject pairing; return to not_configured |
| `diagnose` | — | `dict` | Re-check connection state and capabilities |
| `disconnect` | — | `dict` | Disconnect and reset state to not_configured |
| `forgetServer` | — | `dict` | Clear saved server config and disconnect |
| `addManualServer` | `host: str="", port: int=0, alias: str=""` | `dict` | Save server config and set state to detected |
| `reconnect` | — | `dict` | Attempt reconnection with exponential backoff (max 3 retries) |
| `openHomeAudio` | `route: str="home_audio"` | `dict` | Navigate to home_audio route |
| `refresh` | — | `dict` | Refresh state from controller |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `stateChanged` | — | Emitted when any state property changes |

## Models Exposed
None. All data returned as `QVariantList` properties or slot return dicts.

## Error Handling
- All slots return `dict` with `ok: bool`
- Error format: `{"ok": false, "error": "<CODE>"}`
- Null controller returns `"SERVICE_UNAVAILABLE"`
- Network cancel returns `"CANCELLED"`

## Error Codes
- `SERVICE_UNAVAILABLE` — michi_link_ctrl is None
- `CANCELLED` — operation was cancelled
- `EMPTY_HOST` — host string is empty
- `UNSUPPORTED` — capability not available on controller
- `CONNECTION_FAILED` — testHomeAssistant connection failed

## States (microServerState)
| State | Meaning |
|-------|---------|
| `service_unavailable` | Controller is None |
| `not_configured` | No server configured |
| `scanning` | Discovery in progress |
| `detected` | Server found or manually configured |
| `pairing_required` | Awaiting user pairing confirmation |
| `paired` | Paired but contract not yet verified |
| `connected` | Fully connected with contract |
| `error` | Connection or operation error |

Contract sub-states: `"contract_ok"`, `"contract_partial"`, `"contract_mismatch"` (docstring only, not all implemented).

## Lifecycle
- Created by `BridgeFactory.create_connections_bridge()` with michi_link_ctrl + navigation_bridge
- Initial state: `"service_unavailable"` if no controller, `"not_configured"` if controller exists
- No background timers for status polling; QML must call `refresh()` or `diagnose()`
- `_AsyncOp` provides thread-safe cancellation for async operations

## Behavior When Service Is Null/Missing
- Without `michi_link_ctrl`: all operations return `"SERVICE_UNAVAILABLE"`, state is `"service_unavailable"`
- Without `navigation_bridge`: `openHomeAudio` returns `"UNSUPPORTED"`

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not directly used
- **NavigationBridge**: Used for `openHomeAudio()` slot
- **CapabilityBridge**: Registered as `connections` capability; requires `michi_link_controller`

## Cancellation Contract
- `_cancel_op()` cancels active async operation via `_AsyncOp.cancel()`
- `scanForServers()` cancels any previous operation before starting new one
- Timer-based retry `_retry_timer` is stopped on cancel/disconnect

## Destructive Action Handling
- `forgetServer()` clears saved config from settings
- `disconnect()` resets runtime state without clearing config
- `rejectPair()` returns to not_configured without saving
