# Home Audio Bridge Contract

## Context Property
`HomeAudioBridge` registered as `home_audio` context property.

## Class Name
`HomeAudioBridge` (`ui_qml_bridge/home_audio_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `ha_controller` | `Any (HomeAssistant controller) \| None` | `None` |
| `snapcast_ctrl` | `Any (Snapcast controller) \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `homeAssistantAvailable` | `bool` | constant | Whether HA controller was injected |
| `snapcastAvailable` | `bool` | constant | Whether Snapcast controller is available |
| `receiversAvailable` | `bool` | constant | Always False |
| `zonesSupported` | `bool` | constant | Delegates to snapcastAvailable |
| `groupingSupported` | `bool` | constant | Delegates to snapcastAvailable |
| `volumeSupported` | `bool` | constant | True if either controller available |
| `serverHandoffAvailable` | `bool` | constant | Whether server handoff is supported |
| `homeAssistantState` | `str` | `stateChanged` | HA connection state |
| `snapcastState` | `str` | `stateChanged` | Snapcast availability state |
| `devices` | `QVariantList` | `stateChanged` | Home Assistant media devices |
| `zones` | `QVariantList` | `stateChanged` | Snapcast groups/zones with id, name, muted, volume |
| `receivers` | `QVariantList` | `stateChanged` | Always empty |
| `streams` | `QVariantList` | `stateChanged` | HA streams |
| `groups` | `QVariantList` | `stateChanged` | HA groups |
| `lastError` | `str` | `stateChanged` | Last error message |
| `lastContact` | `float` | `stateChanged` | Unix timestamp of last contact |
| `latencyMs` | `int` | `stateChanged` | Latency in milliseconds |
| `offline` | `bool` | `stateChanged` | True if no contact for 30+ seconds |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Refresh all states from HA and Snapcast controllers |
| `configureHomeAssistant` | `host: str="", port: int=0, token: str=""` | `dict` | Configure HA connection |
| `testHomeAssistant` | — | `dict` | Test HA connection; retry on failure |
| `discoverReceivers` | — | `dict` | Always returns UNSUPPORTED |
| `openDiagnostics` | — | `dict` | Emit stateChanged |
| `setZoneVolume` | `zone_id: str, volume: float=0.5` | `dict` | Set Snapcast group volume |
| `setZoneMute` | `zone_id: str, muted: bool=False` | `dict` | Mute/unmute Snapcast group |
| `assignStream` | `stream_id: str=""` | `dict` | Assign stream to Snapcast |
| `disconnectHa` | — | `dict` | Disconnect HA; reset state |
| `reconnectHa` | — | `dict` | Reconnect HA via testHomeAssistant |
| `serverHandoff` | — | `dict` | Transfer server role to HA/Snapcast |
| `playbackTransfer` | `target_zone_id: str=""` | `dict` | Transfer playback to Snapcast zone |
| `recoverFromOffline` | — | `dict` | Clear offline flag and refresh |
| `getLatencyReport` | — | `dict` | Return latency + offline status |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `stateChanged` | — | Emitted when any state property changes |

## Models Exposed
None. All device/zone/stream data returned as QVariantList.

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"UNSUPPORTED"`, `"NOT_IMPLEMENTED"`, `"CONNECTION_FAILED"`, `"EMPTY_TARGET"`
- Exceptions caught and returned as `{"ok": false, "error": str(e)}`

## Error Codes
- `UNSUPPORTED` — required controller is None
- `NOT_IMPLEMENTED` — controller exists but lacks the method
- `CONNECTION_FAILED` — test connection failed
- `EMPTY_TARGET` — empty target zone ID

## States
- `homeAssistantState`: `"not_configured"`, `"connected"`, `"error"`
- `snapcastState`: `"unavailable"`, `"available"`, `"concept"` (if no controller), `"error"`
- `offline` triggers after 30s without contact

## Lifecycle
- Created by `BridgeFactory.create_home_audio_bridge()` with ha_controller + snapcast_ctrl
- No auto-refresh; QML must call `refresh()` or specific action slots
- Retry with exponential backoff: 2 retries, delay 1500ms * 2^(retry-1), max 10s
- `_retry_timer` single-shot QTimer for backoff management

## Behavior When Service Is Null/Missing
- Without `ha_controller`: HA operations return `"UNSUPPORTED"`, homeAssistantState stays "not_configured"
- Without `snapcast_ctrl`: Snapcast operations return `"UNSUPPORTED"`, snapcastState = "concept"
- Capability properties return False when controller missing

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `home_audio` capability; requires `home_audio_controller`

## Cancellation Contract
- `_cancel_retry()` stops retry timer and resets counter
- `disconnectHa()` cancels any pending retry
- `reconnectHa()` cancels pending retry before attempting

## Destructive Action Handling
- `disconnectHa()` resets state to not_configured
- No explicit destructive actions; all operations reversible
