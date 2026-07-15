# Mix Bridge Contract

## Context Property
`MixBridge` registered as `mix` context property.

## Class Name
`MixBridge` (`ui_qml_bridge/mix_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db` | `Any (Database) \| None` | `None` |
| `playback_ctrl` | `Any \| None` | `None` |
| `player_service` | `Any \| None` | `None` |
| `track_action_service` | `Any \| None` | `None` |
| `playlist_bridge` | `PlaylistsBridge \| None` | `None` |
| `query_service` | `Any (QueryService) \| None` | `None` |
| `query_executor` | `Any \| None` | `None` |
| `worker_manager` | `WorkerManager \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `categories` | `QVariantList` | `dataChanged` | 12 predefined mix categories; filters out ai_recommended if AI disabled |
| `currentSongs` | `QVariantList` | `dataChanged` | Currently loaded mix songs |
| `currentMixTitle` | `str` | `dataChanged` | Title of the current mix |
| `errorMessage` | `str` | `dataChanged` | Last error message |
| `currentMixId` | `str` | `dataChanged` | Current mix category ID |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `loadMix` | `mix_id: str, seed: str=""` | `dict` | Load songs for a mix category; returns ok, count, partial |
| `refresh` | — | `dict` | Reload current mix if one is loaded |
| `playMix` | — | `dict` | Play first track in current mix |
| `enqueueMix` | — | `dict` | Enqueue all tracks in current mix; returns count, errors |
| `saveMixAsPlaylist` | `name: str` | `dict` | Save current mix as a new playlist |
| `playFromIndex` | `index: int` | `dict` | Play track at specific index in mix |
| `cancelGeneration` | — | `dict` | Cancel any ongoing generation via WorkerManager |
| `enqueueTrack` | `index: int` | `dict` | Enqueue single track by index |
| `explainCurrentMix` | — | `dict` | Return reasons for tracks in current mix (first 10) |
| `partialFailureReport` | — | `dict` | Return tracks with errors in current mix |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Properties changed |
| `generationProgress` | `int current, int total` | Progress during async mix generation |
| `generationError` | `str` | Error during generation |

## Models Exposed
None. Songs returned as list of dicts via `currentSongs` property.

## MIX_CATEGORIES (12)
favorites, recent, most_played, unplayed, rediscovery, daily_mix, by_artist, by_genre, by_decade, by_year, high_quality, custom

## Error Handling
- All slots return `dict` with `ok: bool` and optional `error_code`
- Error format: `{"ok": false, "error": "<msg>", "error_code": "<CODE>"}`

## Error Codes
- `EMPTY_MIX` — no songs loaded
- `NO_TRACK_ID` — first track has no identifier
- `PLAY_FAILED` — play action failed
- `NO_PLAYBACK` — no playback service available
- `ENQUEUE_FAILED` — enqueue action failed
- `INVALID_INDEX` — index out of bounds
- `EMPTY_NAME` — playlist name is empty
- `NO_PLAYLIST_BRIDGE` — playlist_bridge is None
- `CREATE_FAILED` — playlist creation failed
- `SAVE_FAILED` — saving mix as playlist failed

## States
- None explicit; `errorMessage` indicates failure state
- `_current_mix_id` empty means no mix loaded

## Lifecycle
- Created by `BridgeFactory.create_mix_bridge()` with db, player_service, optional bridges
- No auto-refresh; `loadMix()` must be called to populate
- `cancelGeneration()` increments generation counter to invalidate stale results

## Behavior When Service Is Null/Missing
- Without `query_service` (`_mqs`): `_load_mix_items` returns empty
- Without `track_action_service`: falls back to `_player` methods (play, enqueue)
- Without `playlist_bridge`: `saveMixAsPlaylist` returns `"NO_PLAYLIST_BRIDGE"`
- Without `worker_manager`: `cancelGeneration` skips WM cancel

## Integration
- **JobService**: Not directly; uses WorkerManager for task cancellation
- **ActionRegistry**: Not used directly
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `mix` capability; requires `db`

## Cancellation Contract
- `cancelGeneration()` increments `_generation` counter + calls `_wm.cancel_all(owner="mix_bridge")`
- Dedup/cancellation is by generation counter, not request ID

## Destructive Action Handling
- `saveMixAsPlaylist` is destructive (creates playlist) but requires explicit name
- No undo feature
