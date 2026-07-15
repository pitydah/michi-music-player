<<<<<<< Updated upstream
<<<<<<< Updated upstream
# RadioBridge Integration Contract
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
# Radio Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `radioBridge` → `RadioBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `stations` | `QVariantList` | `dataChanged` |
| `favorites` | `QVariantList` | `dataChanged` |
| `history` | `QVariantList` | `dataChanged` |

Station schema: `{id: int, name: str, url: str, codec: str, country: str, tags: list, favorite: bool, image_path: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `addStation` | `dict` | `name: str`, `url: str`, `codec: str`, `country: str` |
| `playStation` | `dict` | `url: str`, `name: str = ""` |
| `reconnectLast` | `dict` | none |
| `retryCurrent` | `dict` | none |
| `stopStream` | `dict` | none |
| `cancelStream` | `dict` | none |
| `deleteStation` | `dict` | `url: str` |
| `editStation` | `dict` | `station_id: int`, `name: str`, `url: str`, `codec: str = ""`, `country: str = ""` |
| `toggleFavorite` | `dict` | `station_id: int` |
| `search` | `dict` | `query: str = ""`, `country: str = ""`, `tag: str = ""` |
| `importM3u` | `dict` | `filepath: str` |
| `exportM3u` | `dict` | `filepath: str` |
| `exportOpml` | `dict` | `filepath: str` |
| `getMetadata` | `dict` | `url: str` |
| `getCodec` | `str` | none |
| `getBitrate` | `int` | none |

All dict-returning slots include `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"EMPTY_URL"` — no URL provided for add/play
- `"NO_RADIO_MANAGER"` — RadioManager not injected
- `"NO_PLAYER_SERVICE"` — PlayerService not injected
- `"NO_LAST_STATION"` — no current station for reconnect
- `"NO_PLAYER"` — player stop only
- `"NOT_IMPLEMENTED"` — controller missing method
- `"FILE_NOT_FOUND"` — M3U file not found
- `"NO_STATIONS"` — no stations for export
- `"NO_METADATA"` — metadata service not available
- Exception messages propagated

## Lifecycle Expectations
- Constructor takes optional `radio_manager`, `player_service`.
- `refresh()` queries `RadioManager.get_all()` and populates `stations`/`favorites`.
- History limited to 50 entries (FIFO).

## Behavior When Service Is Missing/Null
- No `_radio_mgr`: `refresh` returns empty, `addStation`/`deleteStation`/`editStation`/`toggleFavorite`/`search`/`importM3u` return `NO_RADIO_MANAGER`.
- No `_player`: `playStation`/`stopStream` return `NO_PLAYER_SERVICE`/`NO_PLAYER`.

## Destructive Actions and Confirmations
- `deleteStation(url)` — deletes a station. No confirmation required in bridge.
- `cancelStream()` — alias for `stopStream()`. No confirmation.

## Cancellation Contract
- `cancelStream()`: calls `PlayerService.stop()`. Idempotent.
- No async cancellation mechanism for import/export.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- `deleteStation(url)` removes station permanently
- No undo; station must be re-added manually
=======
# RadioBridge Integration Contract

## Context Property
- `radioBridge` → `RadioBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `stations` | `QVariantList` | `dataChanged` |
| `favorites` | `QVariantList` | `dataChanged` |
| `history` | `QVariantList` | `dataChanged` |

Station schema: `{id: int, name: str, url: str, codec: str, country: str, tags: list, favorite: bool, image_path: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `addStation` | `dict` | `name: str`, `url: str`, `codec: str`, `country: str` |
| `playStation` | `dict` | `url: str`, `name: str = ""` |
| `reconnectLast` | `dict` | none |
| `retryCurrent` | `dict` | none |
| `stopStream` | `dict` | none |
| `cancelStream` | `dict` | none |
| `deleteStation` | `dict` | `url: str` |
| `editStation` | `dict` | `station_id: int`, `name: str`, `url: str`, `codec: str = ""`, `country: str = ""` |
| `toggleFavorite` | `dict` | `station_id: int` |
| `search` | `dict` | `query: str = ""`, `country: str = ""`, `tag: str = ""` |
| `importM3u` | `dict` | `filepath: str` |
| `exportM3u` | `dict` | `filepath: str` |
| `exportOpml` | `dict` | `filepath: str` |
| `getMetadata` | `dict` | `url: str` |
| `getCodec` | `str` | none |
| `getBitrate` | `int` | none |

All dict-returning slots include `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"EMPTY_URL"` — no URL provided for add/play
- `"NO_RADIO_MANAGER"` — RadioManager not injected
- `"NO_PLAYER_SERVICE"` — PlayerService not injected
- `"NO_LAST_STATION"` — no current station for reconnect
- `"NO_PLAYER"` — player stop only
- `"NOT_IMPLEMENTED"` — controller missing method
- `"FILE_NOT_FOUND"` — M3U file not found
- `"NO_STATIONS"` — no stations for export
- `"NO_METADATA"` — metadata service not available
- Exception messages propagated

## Lifecycle Expectations
- Constructor takes optional `radio_manager`, `player_service`.
- `refresh()` queries `RadioManager.get_all()` and populates `stations`/`favorites`.
- History limited to 50 entries (FIFO).

## Behavior When Service Is Missing/Null
- No `_radio_mgr`: `refresh` returns empty, `addStation`/`deleteStation`/`editStation`/`toggleFavorite`/`search`/`importM3u` return `NO_RADIO_MANAGER`.
- No `_player`: `playStation`/`stopStream` return `NO_PLAYER_SERVICE`/`NO_PLAYER`.

## Destructive Actions and Confirmations
- `deleteStation(url)` — deletes a station. No confirmation required in bridge.
- `cancelStream()` — alias for `stopStream()`. No confirmation.

## Cancellation Contract
- `cancelStream()`: calls `PlayerService.stop()`. Idempotent.
- No async cancellation mechanism for import/export.

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
## Integration with JobService
NOT IMPLEMENTED.

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
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
