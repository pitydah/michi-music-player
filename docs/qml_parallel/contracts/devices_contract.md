<<<<<<< Updated upstream
<<<<<<< Updated upstream
# DevicesBridge Integration Contract
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
# Devices Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `devicesBridge` → `DevicesBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `serverActive` | `bool` | `stateChanged` |
| `serverPort` | `int` | `stateChanged` |
| `peers` | `QVariantList` | `stateChanged` |
| `pairedDevices` | `QVariantList` | `stateChanged` |

Peer schema: `{alias: str, device: str, ip: str, port: int}`
Paired device schema: `{alias: str, device: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `startServer` | `dict` | none |
| `stopServer` | `dict` | none |
| `refresh` | `dict` | none |

All slots return `dict` with `ok: bool`. Errors include `error` string.

## Signals
| Signal | Payload |
|---|---|
| `stateChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"NO_SYNC_MANAGER"` — SyncManager not available
- `"Unexpected result: {type}"` — unhandled return type from SyncManager
- Exception messages propagated as `error` string

## States
None defined explicitly. `serverActive` is the boolean state indicator. No INITIALIZING/LOADING/READY/EMPTY/ERROR states.

## Lifecycle Expectations
- Constructed with optional `SyncManager`; if None, all operations return `NO_SYNC_MANAGER`.
- `refresh()` attempts to query `SyncManager.get_all_peers()` and `get_paired_devices()`.
- `startServer` sets `serverActive=True` only on success; `stopServer` always sets `serverActive=False`.

## Behavior When Service Is Missing/Null
- `_sync_mgr` is `None`: `startServer`, `stopServer` return `{ok: false, error: "NO_SYNC_MANAGER"}`; `refresh` returns `{ok: true, peers: 0, paired: 0}` without error.

## Destructive Actions and Confirmations
None.

## Cancellation Contract
NOT YET IMPLEMENTED — no cancellation mechanism exists.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- `unpairDevice`, `deleteStation` (via protocol) are destructive
- No explicit confirmation; returns result dict
- `clearTransferHistory` is destructive with no undo
=======
# DevicesBridge Integration Contract

## Context Property
- `devicesBridge` → `DevicesBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `serverActive` | `bool` | `stateChanged` |
| `serverPort` | `int` | `stateChanged` |
| `peers` | `QVariantList` | `stateChanged` |
| `pairedDevices` | `QVariantList` | `stateChanged` |

Peer schema: `{alias: str, device: str, ip: str, port: int}`
Paired device schema: `{alias: str, device: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `startServer` | `dict` | none |
| `stopServer` | `dict` | none |
| `refresh` | `dict` | none |

All slots return `dict` with `ok: bool`. Errors include `error` string.

## Signals
| Signal | Payload |
|---|---|
| `stateChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"NO_SYNC_MANAGER"` — SyncManager not available
- `"Unexpected result: {type}"` — unhandled return type from SyncManager
- Exception messages propagated as `error` string

## States
None defined explicitly. `serverActive` is the boolean state indicator. No INITIALIZING/LOADING/READY/EMPTY/ERROR states.

## Lifecycle Expectations
- Constructed with optional `SyncManager`; if None, all operations return `NO_SYNC_MANAGER`.
- `refresh()` attempts to query `SyncManager.get_all_peers()` and `get_paired_devices()`.
- `startServer` sets `serverActive=True` only on success; `stopServer` always sets `serverActive=False`.

## Behavior When Service Is Missing/Null
- `_sync_mgr` is `None`: `startServer`, `stopServer` return `{ok: false, error: "NO_SYNC_MANAGER"}`; `refresh` returns `{ok: true, peers: 0, paired: 0}` without error.

## Destructive Actions and Confirmations
None.

## Cancellation Contract
NOT YET IMPLEMENTED — no cancellation mechanism exists.

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
## Integration with JobService
NOT IMPLEMENTED — no reference to `JobBridge` or `WorkerManager`.

## Integration with ActionRegistry
NOT IMPLEMENTED — no reference to `ActionRegistry`.

## Integration with NavigationBridge
NOT IMPLEMENTED — no reference to `NavigationBridge`.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
