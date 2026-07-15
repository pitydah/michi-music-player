# Lyrics Bridge Contract

## Context Property
`LyricsBridge` registered as `lyrics` context property.

## Class Name
`LyricsBridge` (`ui_qml_bridge/lyrics_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `worker_manager` | `WorkerManager \| None` | `None` |
| `nowplaying_bridge` | `NowPlayingBridge \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `lyrics` | `str` | `dataChanged` | Plain text lyrics |
| `syncedLyrics` | `QVariantList` | `dataChanged` | List of timed lyric lines [{time, text}] |
| `source` | `str` | `dataChanged` | Source name (LRCLIB, local, etc.) |
| `status` | `str` | `dataChanged` | Current status: idle/searching/done/not_found/error |
| `errorMessage` | `str` | `dataChanged` | Last error message |
| `currentTitle` | `str` | `dataChanged` | Title of current search |
| `currentArtist` | `str` | `dataChanged` | Artist of current search |
| `hasSyncedLyrics` | `bool` | `dataChanged` | Whether synced lyrics are available |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `searchCurrentTrack` | — | `dict` | Search lyrics for currently playing track via NowPlayingBridge |
| `search` | `title: str, artist: str, album: str="", duration: int=0` | `dict` | Search lyrics by track info; checks cache first |
| `searchManual` | `query: str` | `dict` | Search lyrics by free-text query |
| `cancelSearch` | — | `void` | Cancel active search; reset status to idle |
| `refresh` | — | `dict` | Re-search for current track |
| `clearCacheForCurrentTrack` | — | `dict` | Remove current track from cache |
| `saveLocalLyrics` | `text: str` | `dict` | Save locally entered lyrics |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Lyrics data or status changed |

## Models Exposed
None. Lyrics returned as plain text + list of timed dicts.

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"NO_NOWPLAYING_BRIDGE"`, `"NOT_FOUND"`, `"EMPTY_QUERY"`
- `status` property tracks searching/done/not_found/error states

## Error Codes
- `NO_NOWPLAYING_BRIDGE` — nowplaying_bridge not injected
- `NOT_FOUND` — LRCLIB returned no results
- `TIMEOUT` — search timed out (15 seconds)
- `EMPTY_QUERY` — empty search query

## States
| Status | Meaning |
|--------|---------|
| `idle` | No active search |
| `searching` | Search in progress |
| `done` | Results found and loaded |
| `not_found` | No results |
| `error` | Search failed |

## Lifecycle
- Created by `BridgeFactory.create_lyrics_bridge()` with worker_manager + nowplaying_bridge
- Auto-searches on track change if `nowplaying_bridge` connected via `trackChanged` signal
- Internal LRU cache (max 50 entries) keyed by `title||artist||album||duration`
- 15-second timeout timer for searches
- Connects to `nowplaying_bridge.trackChanged` on init

## Behavior When Service Is Null/Missing
- Without `worker_manager`: fallback to synchronous search via `QTimer.singleShot(0)`
- Without `nowplaying_bridge`: `searchCurrentTrack()` returns `"NO_NOWPLAYING_BRIDGE"`; auto-search on track change disabled

## Integration
- **JobService**: Uses `WorkerManager.run_task()` for async search
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `lyrics` capability; requires `worker_manager`

## Cancellation Contract
- `cancelSearch()` sets `_active_search_id = 0` (invalidates all pending callbacks)
- Stale search results are discarded by comparing `search_id` with `_active_search_id`
- `_timeout_timer` stopped on cancel, completion, or error

## Destructive Action Handling
- None. Lyrics is read-only from network; `saveLocalLyrics()` is additive.
