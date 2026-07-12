# QML Migration Progress

**Updated:** 2026-07-12
**Overall score:** 66.0% (FUNCTIONAL)

## Module status

| Module | State | Tests | Async | Cancel | Errors |
|---|---|---|---|---|---|
| navigation | FUNCTIONAL | 1 | — | — | ✓ |
| library | FUNCTIONAL | 28 | ✓ | ✓ | ✓ |
| playlists | FUNCTIONAL | 4 | ✓ | ✓ | ✓ |
| queue | FUNCTIONAL | 4 | ✓ | ✓ | ✓ |
| history | FUNCTIONAL | 4 | ✓ | ✓ | ✓ |
| radio | FUNCTIONAL | 2 | — | — | ✓ |
| lyrics | FUNCTIONAL | 9 | — | — | ✓ |
| mix | FUNCTIONAL | 2 | — | — | ✓ |
| home | FUNCTIONAL | 3 | — | — | ✓ |
| settings | SCORE_74 | — | — | — | — |
| eq | SCORE_74 | 3 | — | — | — |
| audio_lab | SCORE_74 | 3 | — | — | — |
| diagnostics | FUNCTIONAL | — | — | — | — |
| app | VISUAL_ONLY | 1 | — | — | — |
| theme | VISUAL_ONLY | 1 | — | — | — |
| metadata | FUNCTIONAL | 2 | — | — | ✓ |
| smart_tagging | FUNCTIONAL | 4 | ✓ | ✓ | ✓ |
| library_doctor | FUNCTIONAL | — | — | — | — |
| disc_lab | SCORE_74 | 4 | — | — | — |
| michi_ai | VISUAL_ONLY | 1 | — | — | — |
| connections | FUNCTIONAL | 3 | — | — | — |
| home_audio | FUNCTIONAL | 9 | — | — | — |
| devices | VISUAL_ONLY | — | — | — | — |
| notification | SCORE_74 | — | — | — | — |
| action_registry | FUNCTIONAL | 4 | — | — | ✓ |
| global_search | FUNCTIONAL | 3 | — | — | ✓ |
| job_bridge | FUNCTIONAL | 4 | ✓ | ✓ | ✓ |
| worker_manager | FUNCTIONAL | — | ✓ | ✓ | — |
| query_executor | FUNCTIONAL | — | ✓ | ✓ | ✓ |
| library_sources | FUNCTIONAL | 8 | — | — | ✓ |
| track_action_service | FUNCTIONAL | — | — | — | ✓ |
| scanner_job_adapter | FUNCTIONAL | — | ✓ | ✓ | — |
| metadata_batch | FUNCTIONAL | — | — | — | — |
| capability | FUNCTIONAL | 1 | — | — | ✓ |
| output_profiles | FUNCTIONAL | — | — | — | — |

## Key

- **State:** VISUAL_ONLY (20) → PARTIAL (40) → FUNCTIONAL (65) → VERIFIED (85) → FULL_PARITY (100)
- **Tests:** number of unit tests referencing this module
- **Async:** runs in background thread via WorkerManager
- **Cancel:** supports cooperative cancellation
- **Errors:** typed error codes returned to QML
