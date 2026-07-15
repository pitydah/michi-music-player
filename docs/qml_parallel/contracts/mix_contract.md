# MixBridge Integration Contract
# Mix Bridge Contract

## Context Property
- `mixBridge` → `MixBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `categories` | `QVariantList` | `dataChanged` |
| `currentSongs` | `QVariantList` | `dataChanged` |
| `currentMixTitle` | `str` | `dataChanged` |
| `errorMessage` | `str` | `dataChanged` |
| `currentMixId` | `str` | `dataChanged` |

Category schema: `{id: str, title: str, icon: str, desc: str}`
Song schema: `{track_id: int/str, id: int, artist: str, title: str, reason: str, _error: str, ...}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `loadMix` | `dict` | `mix_id: str`, `seed: str = ""` |
| `refresh` | `dict` | none |
| `playMix` | `dict` | none |
| `enqueueMix` | `dict` | none |
| `saveMixAsPlaylist` | `dict` | `name: str` |
| `playFromIndex` | `dict` | `index: int` |
| `cancelGeneration` | `dict` | none |
| `enqueueTrack` | `dict` | `index: int` |
| `explainCurrentMix` | `dict` | none |
| `partialFailureReport` | `dict` | none |

All slots return `dict` with `ok: bool`. Error responses include `error_code` and `message`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |
| `generationProgress` | `current: int, total: int` |
| `generationError` | `error: str` |

## Models Exposed
None.

## Error Types/Codes
- `"EMPTY_MIX"` — no songs loaded
- `"NO_TRACK_ID"` — song missing identifier
- `"PLAY_FAILED"` — playback error
- `"NO_PLAYBACK"` / `"NO_PLAYBACK_SERVICE"` — no player available
- `"EMPTY_NAME"` — empty playlist name
- `"NO_PLAYLIST_BRIDGE"` — PlaylistsBridge not injected
- `"CREATE_FAILED"` — playlist creation failed
- `"SAVE_FAILED"` — playlist save failed
- `"INVALID_INDEX"` — index out of range
- `"ENQUEUE_FAILED"` — enqueue error

## Mix Categories (constant)
`favorites`, `recent`, `most_played`, `unplayed`, `rediscovery`, `daily_mix`, `by_artist`, `by_genre`, `by_decade`, `by_year`, `high_quality`, `custom`.

## Lifecycle Expectations
- Constructor takes optional `db`, `playback_ctrl`/`player_service`, `track_action_service`, `playlist_bridge`, `query_service`/`query_executor`, `worker_manager`.
- `loadMix(mix_id)` queries the `MixQueryService` for the given category. Returns partial results (sets `errorMessage` if empty).
- `playMix` plays the first song in `currentSongs`.
- `enqueueMix` enqueues all songs via `TrackActionService`.

## Behavior When Service Is Missing/Null
- No `_mqs` (MixQueryService): `_load_mix_items` returns `[]`. `loadMix` will report empty but NOT error.
- No `_tas`: falls back to `_player` for play/enqueue; if neither exists returns `NO_PLAYBACK`/`NO_PLAYBACK_SERVICE`.
- No `_pb`: `saveMixAsPlaylist` returns `NO_PLAYLIST_BRIDGE`.

## Destructive Actions and Confirmations
None.

## Cancellation Contract
- `cancelGeneration()`: increments `_generation` counter (stale-guard), calls `_wm.cancel_all(owner="mix_bridge")` if WorkerManager available.
- State transitions: none defined — no explicit state machine.

## Destructive Action Handling
- `saveMixAsPlaylist` is destructive (creates playlist) but requires explicit name
- No undo feature
# MixBridge Integration Contract

## Context Property
- `mixBridge` → `MixBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `categories` | `QVariantList` | `dataChanged` |
| `currentSongs` | `QVariantList` | `dataChanged` |
| `currentMixTitle` | `str` | `dataChanged` |
| `errorMessage` | `str` | `dataChanged` |
| `currentMixId` | `str` | `dataChanged` |

Category schema: `{id: str, title: str, icon: str, desc: str}`
Song schema: `{track_id: int/str, id: int, artist: str, title: str, reason: str, _error: str, ...}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `loadMix` | `dict` | `mix_id: str`, `seed: str = ""` |
| `refresh` | `dict` | none |
| `playMix` | `dict` | none |
| `enqueueMix` | `dict` | none |
| `saveMixAsPlaylist` | `dict` | `name: str` |
| `playFromIndex` | `dict` | `index: int` |
| `cancelGeneration` | `dict` | none |
| `enqueueTrack` | `dict` | `index: int` |
| `explainCurrentMix` | `dict` | none |
| `partialFailureReport` | `dict` | none |

All slots return `dict` with `ok: bool`. Error responses include `error_code` and `message`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |
| `generationProgress` | `current: int, total: int` |
| `generationError` | `error: str` |

## Models Exposed
None.

## Error Types/Codes
- `"EMPTY_MIX"` — no songs loaded
- `"NO_TRACK_ID"` — song missing identifier
- `"PLAY_FAILED"` — playback error
- `"NO_PLAYBACK"` / `"NO_PLAYBACK_SERVICE"` — no player available
- `"EMPTY_NAME"` — empty playlist name
- `"NO_PLAYLIST_BRIDGE"` — PlaylistsBridge not injected
- `"CREATE_FAILED"` — playlist creation failed
- `"SAVE_FAILED"` — playlist save failed
- `"INVALID_INDEX"` — index out of range
- `"ENQUEUE_FAILED"` — enqueue error

## Mix Categories (constant)
`favorites`, `recent`, `most_played`, `unplayed`, `rediscovery`, `daily_mix`, `by_artist`, `by_genre`, `by_decade`, `by_year`, `high_quality`, `custom`.

## Lifecycle Expectations
- Constructor takes optional `db`, `playback_ctrl`/`player_service`, `track_action_service`, `playlist_bridge`, `query_service`/`query_executor`, `worker_manager`.
- `loadMix(mix_id)` queries the `MixQueryService` for the given category. Returns partial results (sets `errorMessage` if empty).
- `playMix` plays the first song in `currentSongs`.
- `enqueueMix` enqueues all songs via `TrackActionService`.

## Behavior When Service Is Missing/Null
- No `_mqs` (MixQueryService): `_load_mix_items` returns `[]`. `loadMix` will report empty but NOT error.
- No `_tas`: falls back to `_player` for play/enqueue; if neither exists returns `NO_PLAYBACK`/`NO_PLAYBACK_SERVICE`.
- No `_pb`: `saveMixAsPlaylist` returns `NO_PLAYLIST_BRIDGE`.

## Destructive Actions and Confirmations
None.

## Cancellation Contract
- `cancelGeneration()`: increments `_generation` counter (stale-guard), calls `_wm.cancel_all(owner="mix_bridge")` if WorkerManager available.
- State transitions: none defined — no explicit state machine.

## Integration with JobService
Uses `WorkerManager` (`_wm`) for cancellation of generation tasks via `cancel_all(owner="mix_bridge")`. NOT a full JobBridge integration.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
NOT IMPLEMENTED.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED — though `_ai_enabled` flag exists for conditional category filtering.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
