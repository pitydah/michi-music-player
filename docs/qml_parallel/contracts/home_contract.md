<<<<<<< Updated upstream
# HomeBridge Integration Contract
=======
<<<<<<< HEAD
# Home Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `homeBridge` → `HomeBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `libraryAlbums` | `int` | `snapshotChanged` |
| `libraryArtists` | `int` | `snapshotChanged` |
| `libraryTracks` | `int` | `snapshotChanged` |
| `sourcesCount` | `int` | `snapshotChanged` |
| `lastScan` | `str` | `snapshotChanged` |
| `currentTrackTitle` | `str` | `snapshotChanged` |
| `currentArtist` | `str` | `snapshotChanged` |
| `hasPlayback` | `bool` | `snapshotChanged` |
| `activeJobs` | `int` | `snapshotChanged` |
| `backend` | `str` | `snapshotChanged` |
| `output` | `str` | `snapshotChanged` |

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `homeScore` | `dict` | none |
| `set_library_stats` | (none) | `albums: int`, `artists: int`, `tracks: int` |

## Signals
| Signal | Payload |
|---|---|
| `snapshotChanged` | (none) |

## Models Exposed
None — all state is flat properties.

## Lifecycle Expectations
- Constructor takes optional `db`, `player_service`, `library_bridge`, `library_sources_service`, `job_bridge`.
- Connects to `player_service.track_changed` and `player_service.state_changed` for reactive playback updates.
- Connects to `job_bridge.jobsChanged` for reactive job count updates.
- `refresh()` calls four load methods: `_load_library_stats()`, `_load_playback()`, `_load_sources()`, `_load_jobs()`, `_load_audio()`.

## Behavior When Service Is Missing/Null
- No `_lib` (LibraryBridge): library stats stay 0.
- No `_player`: `hasPlayback` stays False, current track/artist show "—", backend/output empty.
- No `_src_svc`: `sourcesCount` stays 0.
- No `_job_bridge`: `activeJobs` stays 0.

## Destructive Actions and Confirmations
None — dashboard is read-only.

## Cancellation Contract
NOT IMPLEMENTED — no cancellation mechanism.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- None. Home bridge is read-only display.
=======
# HomeBridge Integration Contract

## Context Property
- `homeBridge` → `HomeBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `libraryAlbums` | `int` | `snapshotChanged` |
| `libraryArtists` | `int` | `snapshotChanged` |
| `libraryTracks` | `int` | `snapshotChanged` |
| `sourcesCount` | `int` | `snapshotChanged` |
| `lastScan` | `str` | `snapshotChanged` |
| `currentTrackTitle` | `str` | `snapshotChanged` |
| `currentArtist` | `str` | `snapshotChanged` |
| `hasPlayback` | `bool` | `snapshotChanged` |
| `activeJobs` | `int` | `snapshotChanged` |
| `backend` | `str` | `snapshotChanged` |
| `output` | `str` | `snapshotChanged` |

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `homeScore` | `dict` | none |
| `set_library_stats` | (none) | `albums: int`, `artists: int`, `tracks: int` |

## Signals
| Signal | Payload |
|---|---|
| `snapshotChanged` | (none) |

## Models Exposed
None — all state is flat properties.

## Lifecycle Expectations
- Constructor takes optional `db`, `player_service`, `library_bridge`, `library_sources_service`, `job_bridge`.
- Connects to `player_service.track_changed` and `player_service.state_changed` for reactive playback updates.
- Connects to `job_bridge.jobsChanged` for reactive job count updates.
- `refresh()` calls four load methods: `_load_library_stats()`, `_load_playback()`, `_load_sources()`, `_load_jobs()`, `_load_audio()`.

## Behavior When Service Is Missing/Null
- No `_lib` (LibraryBridge): library stats stay 0.
- No `_player`: `hasPlayback` stays False, current track/artist show "—", backend/output empty.
- No `_src_svc`: `sourcesCount` stays 0.
- No `_job_bridge`: `activeJobs` stays 0.

## Destructive Actions and Confirmations
None — dashboard is read-only.

## Cancellation Contract
NOT IMPLEMENTED — no cancellation mechanism.

>>>>>>> Stashed changes
## Integration with JobService
- Reads `job_bridge.activeCount` for dashboard display.
- Connects to `job_bridge.jobsChanged` for reactive updates.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
NOT IMPLEMENTED.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
