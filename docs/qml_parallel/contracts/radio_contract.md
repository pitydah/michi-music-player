# Radio Bridge Contract

## Context Property
`RadioBridge` registered as `radio` context property.

## Class Name
`RadioBridge` (`ui_qml_bridge/radio_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `radio_manager` | `Any (RadioManager) \| None` | `None` |
| `player_service` | `Any \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `stations` | `QVariantList` | `dataChanged` | All radio stations with id, name, url, codec, country, tags, favorite, image_path |
| `favorites` | `QVariantList` | `dataChanged` | Favorite stations only |
| `history` | `QVariantList` | `dataChanged` | Recently played stations (max 50) with name, url, played_at |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Reload all stations from radio_manager; returns count |
| `addStation` | `name: str, url: str, codec: str="", country: str=""` | `dict` | Add a new radio station |
| `playStation` | `url: str, name: str=""` | `dict` | Play a station URL; adds to history |
| `reconnectLast` | — | `dict` | Reconnect to the last played station |
| `retryCurrent` | — | `dict` | Alias for reconnectLast |
| `stopStream` | — | `dict` | Stop current stream via player_service |
| `cancelStream` | — | `dict` | Alias for stopStream |
| `deleteStation` | `url: str` | `dict` | Remove a station |
| `editStation` | `station_id: int, name: str, url: str, codec: str="", country: str=""` | `dict` | Update station metadata |
| `toggleFavorite` | `station_id: int` | `dict` | Toggle favorite status; returns new favorite state |
| `search` | `query: str="", country: str="", tag: str=""` | `dict` | Search stations by name, country, tag |
| `importM3u` | `filepath: str` | `dict` | Import stations from M3U file |
| `exportM3u` | `filepath: str` | `dict` | Export all stations to M3U file |
| `exportOpml` | `filepath: str` | `dict` | Export all stations to OPML file |
| `getMetadata` | `url: str` | `dict` | Get stream metadata for a URL |
| `getCodec` | — | `str` | Return codec of first station (legacy) |
| `getBitrate` | — | `int` | Always returns 0 (legacy) |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Stations, favorites, or history changed |

## Models Exposed
None. Stations returned as list of dicts.

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"EMPTY_URL"`, `"NO_RADIO_MANAGER"`, `"NO_PLAYER_SERVICE"`, `"FILE_NOT_FOUND"`, `"NO_STATIONS"`, `"NO_METADATA"`, `"NO_LAST_STATION"`, `"NOT_IMPLEMENTED"`

## Error Codes
- `NO_RADIO_MANAGER` — radio_manager is None
- `NO_PLAYER_SERVICE` — player_service is None
- `EMPTY_URL` — empty station URL
- `FILE_NOT_FOUND` — import/export file doesn't exist
- `NO_STATIONS` — no stations to export
- `NO_LAST_STATION` — no previously played station
- `NOT_IMPLEMENTED` — manager exists but method not available

## States
- None explicit; `dataChanged` signals any change
- `_current_station` tracks the last played station URL

## Lifecycle
- Created by `BridgeFactory.create_radio_bridge()` with radio_manager + player_service
- No internal timers; `refresh()` must be called explicitly
- History capped at 50 entries

## Behavior When Service Is Null/Missing
- Without `radio_manager`: `refresh()` returns empty lists, station operations return `"NO_RADIO_MANAGER"`
- Without `player_service`: `playStation()` returns `"NO_PLAYER_SERVICE"`

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `radio` capability; requires `radio_manager`

## Cancellation Contract
- `cancelStream()` aliases `stopStream()`
- No async task IDs or generation counters

## Destructive Action Handling
- `deleteStation(url)` removes station permanently
- No undo; station must be re-added manually
