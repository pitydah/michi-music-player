# Home Bridge Contract

## Context Property
`HomeBridge` registered as `home` context property.

## Class Name
`HomeBridge` (`ui_qml_bridge/home_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db` | `Any (Database) \| None` | `None` |
| `player_service` | `Any (PlayerService) \| None` | `None` |
| `library_bridge` | `LibraryBridge \| None` | `None` |
| `library_sources_service` | `Any \| None` | `None` |
| `job_bridge` | `JobBridge \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `libraryAlbums` | `int` | `snapshotChanged` | Total album count |
| `libraryArtists` | `int` | `snapshotChanged` | Total artist count |
| `libraryTracks` | `int` | `snapshotChanged` | Total track count |
| `sourcesCount` | `int` | `snapshotChanged` | Number of library sources |
| `lastScan` | `str` | `snapshotChanged` | Last scan timestamp |
| `currentTrackTitle` | `str` | `snapshotChanged` | Currently playing track title |
| `currentArtist` | `str` | `snapshotChanged` | Currently playing track artist |
| `hasPlayback` | `bool` | `snapshotChanged` | Whether something is playing |
| `activeJobs` | `int` | `snapshotChanged` | Count of active background jobs |
| `backend` | `str` | `snapshotChanged` | Active audio backend ID |
| `output` | `str` | `snapshotChanged` | Active output device ID |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `void` | Reload all dashboard stats from services |
| `homeScore` | — | `dict` | Return capability score (0-100) with sub-metrics |
| `set_library_stats` | `albums: int, artists: int, tracks: int` | `void` | Manually set library stats |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `snapshotChanged` | — | Any snapshot property changed |

## Models Exposed
None. All data via individual properties.

## Error Handling
- No explicit error return; all internal loads use try/except and silently skip on failure
- `homeScore()` returns dict with sub-metrics including `has_db`, `has_player`

## States
- None explicit; `snapshotChanged` signals full state refresh
- `hasPlayback` boolean derived from current track

## Lifecycle
- Created by `BridgeFactory.create_home_bridge()` with db, player_service, library_bridge, job_bridge
- Connects to `player_service.track_changed` and `player_service.state_changed` for live updates
- Connects to `job_bridge.jobsChanged` for active job count updates
- `refresh()` aggregates data from: library_bridge → counts, player_service → playback + audio, library_sources_service → sources, job_bridge → active jobs

## Behavior When Service Is Null/Missing
- Without `library_bridge`: counts stay at 0
- Without `player_service`: playback info shows "—", backend/output empty
- Without `library_sources_service`: sourcesCount = 0
- Without `job_bridge`: activeJobs = 0
- Without `db`: homeScore score reduced

## Integration
- **JobService**: Reads `job_bridge.activeCount` for active jobs display
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `home` capability; requires `db`

## Cancellation Contract
- None. Home bridge is read-only (displays snapshot of other services).

## Destructive Action Handling
- None. Home bridge is read-only display.
