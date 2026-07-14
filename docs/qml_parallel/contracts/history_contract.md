# HistoryBridge Integration Contract

## Context Property
- `historyBridge` → `HistoryBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `historyModel` | `QVariant` (HistoryListModel) | `dataChanged` |
| `historyCount` | `int` | `dataChanged` |
| `historyQueryService` | `QVariant` | `dataChanged` |
| `playbackBridge` | `QVariant` | `dataChanged` |

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | `dict` | none |
| `removeHistoryItem` | `dict` | `track_id: str` |
| `removeHistoryEvent` | `dict` | `event_id: str` |
| `clearHistory` | `dict` | none |
| `exportHistory` | `dict` | `filepath: str`, `fmt: str = "json"` |
| `cancelExport` | `dict` | `export_id: str`, `filepath: str = ""` |
| `playHistoryItem` | `dict` | `track_id: str` |
| `applyRetention` | `dict` | `config_json: str` |
| `getStatistics` | `dict` | none |
| `setHistoryEnabled` | `dict` | `enabled: bool` |
| `setHistoryLimit` | `dict` | `limit: int` |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
- `HistoryListModel` (registered as `historyModel`) — QML ListModel-compatible via `QVariant`.

## Error Types/Codes
- `"NO_DB"` — no database connection
- `"NO_SERVICE"` — no HistoryQueryService
- `"INVALID_ID"` — event_id not parseable as int
- `"EMPTY_PATH"` — no filepath for export
- `"NO_PLAYBACK"` — no playback service for play

## Lifecycle Expectations
- Constructor takes optional `db`, `history_query_service`, `query_executor`, `playback_service`, `action_registry`.
- Internally creates `HistoryListModel(parent=self)` with same dependencies.
- `playbackBridge` can be set dynamically via `setPlaybackBridge()`.

## Behavior When Service Is Missing/Null
- No `_hqs`: `removeHistoryItem` falls back to raw SQL on `_db`. `removeHistoryEvent` returns `NO_SERVICE`. `clearHistory` falls back to raw SQL. `exportHistory` falls back to raw SQL. `applyRetention` returns `NO_SERVICE`. `getStatistics` falls back to raw SQL `COUNT(*)`. `setHistoryEnabled`/`setHistoryLimit` return `{ok: true}` (no-op).
- No `_playback_svc` and no `_action_registry`: `playHistoryItem` returns `NO_PLAYBACK`.

## Destructive Actions and Confirmations
- `clearHistory()` — deletes all play history. No confirmation required.
- `removeHistoryItem(track_id)` / `removeHistoryEvent(event_id)` — removes entries. No confirmation.

## Cancellation Contract
- `cancelExport(export_id, filepath)`: removes the export file from disk if `filepath` provided and exists. Returns `cancelled: true`.

## Integration with JobService
NOT IMPLEMENTED.

## Integration with ActionRegistry
- `playHistoryItem(track_id)` falls back to `action_registry.execute("track_play_now")` if no playback service.

## Integration with NavigationBridge
NOT IMPLEMENTED.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
