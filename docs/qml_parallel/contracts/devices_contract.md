# Devices Bridge Contract

## Context Property
`DevicesBridge` registered as `devices` context property.

## Class Name
`DevicesBridge` (`ui_qml_bridge/devices_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `sync_manager` | `SyncManager \| None` | `None` |
| `device_sync_service` | `Any \| None` | `None` |
| `job_service` | `Any \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `serverActive` | `bool` | `stateChanged` | Whether the sync server is running |
| `serverPort` | `int` | `stateChanged` | Port the sync server listens on (default 53318) |
| `peers` | `QVariantList` | `stateChanged` | List of discovered sync peers with alias, device, ip, port |
| `pairedDevices` | `QVariantList` | `stateChanged` | List of paired devices with alias, device, vendor, model |
| `discovered` | `QVariantList` | `stateChanged` | List of discovered USB mass-storage devices |
| `storageInfo` | `QVariantList` | `stateChanged` | Storage capacity info per device |
| `compatibilityInfo` | `QVariantList` | `stateChanged` | Device capabilities info |
| `transferJobs` | `QVariantList` | `stateChanged` | Active file transfer jobs |
| `transferHistory` | `QVariantList` | `stateChanged` | Completed transfer history |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `startServer` | — | `dict` | Start the sync server; sets serverActive on success |
| `stopServer` | — | `dict` | Stop the sync server; always clears serverActive |
| `refresh` | — | `dict` | Refresh all peers, paired devices, server state |
| `discoverDevices` | — | `dict` | Discover USB mass-storage devices; returns count |
| `pairDevice` | `mount_point: str` | `dict` | Pair a discovered device by mount point |
| `unpairDevice` | `key: str` | `dict` | Remove pairing for a device by key |
| `trustDevice` | `key: str` | `dict` | Trust a paired device |
| `deviceDetailStorage` | `mount_point: str` | `dict` | Get storage info for a device |
| `deviceDetailCompatibility` | `mount_point: str` | `dict` | Get compatibility/capabilities for a device |
| `startTransfer` | `src: str, dst: str` | `dict` | Start a file transfer; validates audio extensions |
| `cancelTransfer` | `job_id: str` | `dict` | Cancel an active transfer job |
| `retryTransfer` | `job_id: str` | `dict` | Retry a failed transfer job |
| `validateAudioFile` | `path: str` | `dict` | Validate file is supported audio; returns transcode policy |
| `clearTransferHistory` | — | `dict` | Clear all transfer history |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `stateChanged` | — | Emitted when any property changes |

## Models Exposed
None. All data returned as `QVariantList` via properties.

## Error Handling
- All slots return `dict` with `ok: bool` key
- Error format: `{"ok": false, "error": "<CODE>", "message": "<text>"}`
- Null/missing service returns `"NO_SYNC_MANAGER"` or `"NO_DEVICE_SYNC_SERVICE"`
- File validation errors: `"VIDEO_NOT_SUPPORTED"`, `"UNSUPPORTED_FORMAT"`, `"FILE_NOT_FOUND"`
- All exceptions caught and returned as `{"ok": false, "error": "<exception message>"}`

## Error Codes
- `NO_SYNC_MANAGER` — sync_manager dependency is None
- `NO_DEVICE_SYNC_SERVICE` — device_sync_service dependency is None
- `NOT_FOUND` — device not found during identify
- `VIDEO_NOT_SUPPORTED` — video files cannot be transferred
- `UNSUPPORTED_FORMAT` — unrecognized audio extension
- `FILE_NOT_FOUND` — source file does not exist

## States
- Server states: `serverActive` true/false
- Transfer job states come from `device_sync_svc.list_jobs()`

## Lifecycle
- Created by `BridgeFactory.create_devices_bridge()` with optional dependencies
- No internal timers or auto-refresh; QML must call `refresh()` explicitly
- `stateChanged` emitted after all mutating operations

## Behavior When Service Is Null/Missing
- All slots check `_sync_mgr` and `_device_sync_svc` before operations
- If missing, return typed error with `"NO_SYNC_MANAGER"` or `"NO_DEVICE_SYNC_SERVICE"`
- Properties return empty defaults (empty lists, `serverActive=False`)

## Integration
- **JobService**: Used if provided for job tracking; not directly wired in factory
- **ActionRegistry**: Not directly used
- **NavigationBridge**: Not directly used
- **CapabilityBridge**: Registered as `devices` capability; requires `sync_manager`

## Cancellation Contract
- `cancelTransfer(job_id)` cancels via `device_sync_svc.cancel_job()`
- No generation/task cancellation (unlike Mix or Audio Lab)

## Destructive Action Handling
- `unpairDevice`, `deleteStation` (via protocol) are destructive
- No explicit confirmation; returns result dict
- `clearTransferHistory` is destructive with no undo
