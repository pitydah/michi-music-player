# Diagnostics Bridge Contract

## Context Property
`DiagnosticsBridge` registered as `diagnostics` context property.

## Class Name
`DiagnosticsBridge` (`ui_qml_bridge/diagnostics_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `player_service` | `Any (PlayerService) \| None` | `None` |
| `db` | `Any (Database) \| None` | `None` |
| `radio_manager` | `Any \| None` | `None` |
| `sync_manager` | `Any \| None` | `None` |
| `worker_manager` | `WorkerManager \| None` | `None` |
| `query_executor` | `Any \| None` | `None` |
| `library_bridge` | `LibraryBridge \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `jobs` | `QVariantList` | `diagnosticsUpdated` | List of diagnostic check results with id, status, value, message, duration_ms |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Run all diagnostic checks; returns env_info |
| `copyDiagnostics` | — | `str` | Return formatted diagnostics text for clipboard |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Environment info updated |
| `diagnosticsUpdated` | `list` | Diagnostic job results updated (emitted per-job as they complete) |

## Models Exposed
None. Results emitted via `diagnosticsUpdated` list signal as each job completes.

## Checks Run (5)
| Job ID | Function | Pass Condition |
|--------|----------|----------------|
| `database.integrity` | `_check_db_integrity` | PRAGMA integrity_check == "ok" |
| `library.status` | `_check_library_status` | Tracks exist with metadata |
| `player.status` | `_check_player_status` | Player available with backend/volume |
| `storage.paths` | `_check_storage_paths` | All XDG paths resolvable |
| `services.availability` | `_check_services_availability` | All expected services present |

## Error Handling
- Jobs return dict with `status`, `value`, `message`
- Status values: `"PASS"`, `"WARN"`, `"FAIL"`, `"UNKNOWN"`
- No slot-level errors; failures captured per-check

## Error Codes
- Not applicable (failures captured as check status)
- Worker unavailable: `{"id": "worker.unavailable", "status": "FAIL", "value": False}`

## States
- None explicit; `diagnosticsUpdated` emitted per-job as each completes
- `_env_info` cached on each `refresh()` call

## Lifecycle
- Created by `BridgeFactory.create_diagnostics_bridge()` with player_service, db, radio_manager, sync_manager, worker_manager, library_bridge
- `refresh()` runs all 5 checks asynchronously via WorkerManager
- Each check emits `diagnosticsUpdated` when it completes (progressive UI update)

## Behavior When Service Is Null/Missing
- Without `worker_manager`: single synthetic job `"worker.unavailable"` added as FAIL
- Without `db`: database checks return FAIL with "Base de datos no disponible"
- Without `player_service`: player check returns WARN with "Player no disponible"

## Integration
- **JobService**: Not used directly; uses WorkerManager for async checks
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `diagnostics` capability; requires `db`

## Cancellation Contract
- No explicit cancellation of running diagnostic checks
- WorkerManager tasks are cancellable but diagnostics bridge doesn't expose cancel

## Destructive Action Handling
- None. Diagnostics is read-only.
