# Audio Lab Convergence Baseline

Baseline date: 2026-07-19  
Branch: `refactor/premium-ui-system`  
Baseline commit: `5b5d8ab8`

## Focused Test Baseline

Command scope: core Audio Lab tests, QML Audio Lab tests, productive and
specialized workflows, responsive and accessibility coverage.

| Result | Count |
|---|---:|
| Collected | 484 |
| Passed | 395 |
| Failed | 47 |
| Errors | 38 |
| XPASS placeholders | 4 |
| Warnings | 1 |

The four XPASS cases are pass-only placeholder tests in
`test_audio_lab_job_adapter.py`, `test_audio_lab_profile_service.py`,
`test_audio_lab_state.py`, and `test_audio_lab_sync.py`. They are not coverage.

## Canonical Ownership

| Domain | Current canonical owner | Divergence at baseline |
|---|---|---|
| Routes | `ui_qml_bridge/route_registry.py` | `_hub` routes emitted by bridge |
| Jobs | Intended: `AudioLabJobAdapter` + `WorkerManager` | At least seven registries |
| Profiles | `AudioLabProfileService` | Memory-only; divergent dataclass |
| Capabilities | `CapabilityBridge` | Factory map remains empty |
| Confirmation | `ConfirmationService` | Normalization accepts any token |
| Diagnostics | `DiagnosticsCache` | Unversioned schema and partial sync |
| Library state | `media_items` | `NULL` versus `pending`; runtime ALTER |
| QML state | `AudioLabState` | Separate active-job registry |
| Navigation | `NavigationBridge` | Legacy aliases and orphan hubs |
| Job history | Intended durable job storage | Audio Lab jobs remain memory-only |

## QML Contract Divergences

| Page | QML invocation | Actual bridge | Baseline result |
|---|---|---|---|
| Conversion | `startConversion(path, json)` | Two-argument slot | Profile constructor failed |
| Conversion | `preview(path)` | `previewConversion(path, format)` | Missing method |
| Conversion | `activeJobs` list property | `activeJobs()` dictionary slot | Schema mismatch |
| Normalization | `startNormalization(path, token, mode)` | Two-argument slot | Wrong arity |
| ReplayGain | `startReplayGain(path, mode, preamp, headroom)` | One-argument slot returning string | Wrong arity and result |
| ReplayGain | `clearReplayGain(path)` | Missing | Blocked |
| Comparison | `compareFiles(a, b)` | `previewComparison(a, b)` | Missing method |
| Integrity | Reads `valid` | Returns `is_valid` | Schema mismatch |
| CD | `getSpaceInfo()` | Missing | Guarded but disconnected |
| ADC | Uses `root.detectingDevices` | Root ID is `page` | Reference error |

## Job-System Divergences

Competing stores at baseline:

1. `WorkerManager._handles`
2. `AudioLabJobAdapter._jobs`
3. `AudioLabBridge._active_jobs`
4. `AudioConversionService._active_jobs`
5. `AudioBatchService._active/_history`
6. `DurableJobService._jobs/_active`
7. `JobBridge._jobs`

`AudioLabBridge` expects `ProcessController.run_in_thread/cancel` and
`DurableJobService.cancel/status`; those methods do not exist. Production thus
falls back to synchronous execution for analysis, ReplayGain, integrity, and
comparison.

## Canonical Route Decision

`AudioLabHubPage.qml` is the sole Audio Lab root. `AudioLabOverviewPage.qml`
and `pages/assistant/AudioLabPage.qml` are legacy/orphan surfaces and must not
define independent contracts.

Canonical feature routes are the dotted `audio_lab.*` routes in the registry.
Legacy route spellings may exist only as aliases during convergence.

## Synthetic Fixtures

`tests/fixtures/audio_lab_factory.py` generates deterministic non-commercial
audio. WAV fixtures require only Python. FLAC, MP3, Opus, and AAC are derived
with FFmpeg when available. The corpus includes silence, clipping,
multichannel, Hi-Res, empty, truncated, metadata and no-metadata cases.

## Immediate Safety Gates

- No synchronous fallback when `WorkerManager` is missing.
- No destructive normalization until confirmation tokens are bound and single-use.
- No automatic ReplayGain write until write/read verification is implemented.
- No CD/ADC availability claim without tools, platform, permissions and hardware.
- No QML method call without a matching Qt meta-object method and arity.
