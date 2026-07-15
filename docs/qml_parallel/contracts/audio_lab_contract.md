# Audio Lab Bridge Contract

## Context Property
`AudioLabBridge` registered as `audio_lab` context property.

## Class Name
`AudioLabBridge` (`ui_qml_bridge/audio_lab_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db_conn` | `Any (DB connection) \| None` | `None` |
| `navigation_bridge` | `NavigationBridge \| None` | `None` |
| `player_service` | `Any \| None` | `None` |
| `worker_manager` | `WorkerManager \| None` | `None` |
| `audio_lab_service` | `AudioLabService \| None` | `None` |
| `audio_lab_state` | `AudioLabState \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `modules` | `QVariantList` | `dataChanged` | Available modules with id, title, desc, status |
| `totalTracks` | `int` | `dataChanged` | Total tracks in library |
| `missingMetadata` | `int` | `dataChanged` | Tracks missing metadata |
| `missingCovers` | `int` | `dataChanged` | Tracks missing album art |
| `backendInfo` | `QVariantMap` | `dataChanged` | Active backend info |
| `pipelineInfo` | `QVariantMap` | `dataChanged` | Pipeline device, sample_rate, bit_depth, channels |
| `dspInfo` | `QVariantMap` | `dataChanged` | EQ enabled, preamp |
| `selectedProfile` | `str` | `dataChanged` (read/write) | Currently selected AudioLab profile |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Refresh all stats, backend, pipeline info |
| `navigateTo` | `module_id: str` | `dict` | Navigate to an Audio Lab sub-section |
| `capabilities` | — | `QVariantMap` | Return service capability map |
| `inputs` | — | `QVariantList` | Return current inputs from state |
| `profiles` | — | `QVariantList` | Return available profiles |
| `preview` | — | `QVariantMap` | Return preview data |
| `startAnalysis` | `filepath: str` | `dict` | Submit analysis job |
| `startConversion` | `filepath: str` | `dict` | Submit conversion job |
| `startReplayGain` | `filepath: str` | `dict` | Submit ReplayGain job |
| `startNormalization` | `filepath: str` | `dict` | Submit normalization job |
| `startIntegrity` | `filepath: str` | `dict` | Submit integrity check job |
| `startComparison` | `file_a: str, file_b: str` | `dict` | Submit comparison job |
| `cancelJob` | `job_id: str` | `dict` | Cancel a job |
| `retryJob` | `job_id: str` | `dict` | Retry a failed/cancelled job |
| `clearInputs` | — | `dict` | Clear all inputs |
| `results` | — | `QVariantList` | Return results from state |
| `errors` | — | `QVariantList` | Return errors from state |
| `probeFile` | `filepath: str` | `dict` | Probe a file (legacy) |
| `analyzeFile` | `filepath: str` | `dict` | Analyze a file (legacy) |
| `integrityCheck` | `filepath: str, quick: bool=False` | `dict` | Quick integrity check (legacy) |
| `compareFiles` | `file_a: str, file_b: str` | `dict` | Compare two files (legacy) |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Properties changed |

## Models Exposed
None. All data via `QVariantList`/`QVariantMap` properties.

## Error Handling
- Canonical API returns `dict` with `ok: bool`
- Error format: `{"ok": false, "error": "<CODE>"}`
- Legacy slots return varied dict formats with filepath, status, error

## Error Codes
- `NO_SERVICE` — audio_lab_service is None or probe unavailable
- `NO_STATE` — audio_lab_state is None
- `UNSUPPORTED` — navigation route not found
- `NOT_FAILED` — job not in failed/cancelled state for retry

## States
- `selectedProfile` writable property
- Module statuses: `"available"`, `"experimental"`
- Legacy services (diagnostics, health, metadata_doctor) availability depends on backend + DB

## Lifecycle
- Created by `BridgeFactory.create_audio_lab_bridge()` with db_conn, worker_manager, player_service
- `_svc()` and `_state()` return None if service/state not injected or unavailable
- Legacy slots create ad-hoc services if primary not available
- `refresh()` repopulates all stats from DB + backend

## Behavior When Service Is Null/Missing
- Without `audio_lab_service`: canonical job APIs return `"NO_SERVICE"`, capabilities empty
- Without `audio_lab_state`: inputs/profiles/preview/results/errors return empty
- Legacy slots (`probeFile`, `analyzeFile`, `integrityCheck`, `compareFiles`) create ad-hoc services
- Without `player_service`: backend info unavailable, diagnostics module hidden
- Without `db_conn`: health/doctor modules hidden

## Integration
- **JobService**: Not directly; uses `audio_lab_service.jobs` for job management
- **ActionRegistry**: Not used
- **NavigationBridge**: Used for `navigateTo()` route mapping
- **CapabilityBridge**: Registered as `audio_lab` capability; requires `db_connection`

## Cancellation Contract
- `cancelJob(job_id)` cancels via `svc.jobs.cancel()` + removes from state
- `retryJob(job_id)` checks job is in failed/cancelled state
- Legacy slots have no cancellation mechanism

## Destructive Action Handling
- `clearInputs()` clears all pending input state
- Job cancellation is reversible via retry
- No file deletion or permanent data loss
