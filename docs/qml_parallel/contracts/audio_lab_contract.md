# AudioLabBridge Integration Contract

## Context Property
- `audioLabBridge` → `AudioLabBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `modules` | `QVariantList` | `dataChanged` |
| `totalTracks` | `int` | `dataChanged` |
| `missingMetadata` | `int` | `dataChanged` |
| `missingCovers` | `int` | `dataChanged` |
| `backendInfo` | `QVariantMap` | `dataChanged` |
| `pipelineInfo` | `QVariantMap` | `dataChanged` |
| `dspInfo` | `QVariantMap` | `dataChanged` |

Module schema: `{id: str, title: str, desc: str, status: str}` — status: `"available"` or `"experimental"`.
BackendInfo schema: `{backend: str, available: bool}`
DspInfo schema: `{eq_enabled: bool, preamp: float}`
PipelineInfo schema: `{device: str, sample_rate: int, bit_depth: int, channels: int}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `navigateTo` | `dict` | `module_id: str` |
| `probeFile` | `dict` | `filepath: str` |
| `analyzeFile` | `dict` | `filepath: str` |
| `integrityCheck` | `dict` | `filepath: str`, `quick: bool = False` |
| `compareFiles` | `dict` | `file_a: str`, `file_b: str` |

All slots return `dict`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"UNSUPPORTED"` — module route not recognized
- `"UNSUPPORTED"` (format) — file probe/analyze failed
- Error messages propagated from service exceptions.

## Module IDs
`diagnostics`, `health`, `metadata_doctor`, `conversion`, `vinyl`, `analyzer`, `overview`, `analysis`, `normalization`, `replaygain`, `integrity`, `comparison`, `jobs`, `profiles`.

## Routes (for navigateTo)
| Module ID | Route |
|---|---|
| `diagnostics` | `diagnostics` |
| `health` | `library_doctor` |
| `metadata_doctor` | `metadata_inspector` |
| `overview` | `audio_lab_overview` |
| `analysis` | `audio_lab_analysis` |
| `conversion` | `audio_lab_conversion` |
| `normalization` | `audio_lab_normalization` |
| `replaygain` | `audio_lab_replaygain` |
| `integrity` | `audio_lab_integrity` |
| `comparison` | `audio_lab_comparison` |
| `jobs` | `audio_lab_jobs` |
| `profiles` | `audio_lab_profiles` |

## Lifecycle Expectations
- Constructor takes optional `db_conn`, `navigation_bridge`, `player_service`, `worker_manager`.
- `modules` property conditionally includes items based on backend availability (`_check_backend()`) and DB availability.
- `refresh()` populates `_backend_info`, `_dsp_info`, `_pipeline_info`, `_health`/`_stats` from real services.
- `compute_health(db_conn)` called from `core.audio_lab.library_health`.

## Behavior When Service Is Missing/Null
- No `_player` or no `get_active_backend_id()`: backend-dependent modules (`diagnostics`, `metadata_doctor`) excluded from `modules`. `backendInfo` shows `available: false`.
- No `_conn`: health-dependent modules (`health`, `metadata_doctor`) excluded. `stats` empty.
- No `_nav`: `navigateTo` returns `UNSUPPORTED`.

## Destructive Actions and Confirmations
None — all operations are read-only analysis/probe/check.

## Cancellation Contract
NOT IMPLEMENTED — no cancellation mechanism for long-running tasks.

## Integration with JobService
NOT IMPLEMENTED — `worker_manager` is accepted in constructor but not used.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
- `navigateTo(module_id)`: resolves module ID to route via `route_map`, calls `_nav.navigate(route)`.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED — availability is self-detected from `_player` and `_conn`.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
