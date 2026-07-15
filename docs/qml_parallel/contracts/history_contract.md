# History Bridge Contract

## Context Property
`HistoryBridge` registered as `history` context property.

## Class Name
`HistoryBridge` (`ui_qml_bridge/history_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db` | `Any (Database) \| None` | `None` |
| `history_query_service` | `Any \| None` | `None` |
| `query_executor` | `Any \| None` | `None` |
| `playback_service` | `Any \| None` | `None` |
| `action_registry` | `ActionRegistry \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `historyModel` | `QVariant` | `dataChanged` | `HistoryListModel` QML model instance |
| `historyCount` | `int` | `dataChanged` | Total count from model |
| `historyQueryService` | `QVariant` | `dataChanged` | Raw query service reference |
| `playbackBridge` | `QVariant` | `dataChanged` | Associated playback bridge if set |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Refresh model data |
| `removeHistoryItem` | `track_id: str` | `dict` | Remove a specific track from history |
| `removeHistoryEvent` | `event_id: str` | `dict` | Remove a specific playback event |
| `clearHistory` | — | `dict` | Clear entire play history |
| `exportHistory` | `filepath: str, fmt: str="json"` | `dict` | Export history to file |
| `cancelExport` | `export_id: str, filepath: str=""` | `dict` | Cancel export and clean up file |
| `playHistoryItem` | `track_id: str` | `dict` | Play a track from history |
| `applyRetention` | `config_json: str` | `dict` | Apply retention policy (max_age_days) |
| `getStatistics` | — | `dict` | Return play statistics |
| `setHistoryEnabled` | `enabled: bool` | `dict` | Enable/disable history recording |
| `setHistoryLimit` | `limit: int` | `dict` | Set history size limit |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | History data or count changed |

## Models Exposed
| Model | Purpose |
|-------|---------|
| `HistoryListModel` (`ui_qml/models/HistoryListModel.py`) | QML-accessible model of play history events |

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"NO_DB"`, `"NO_SERVICE"`, `"NO_PLAYBACK"`, `"INVALID_ID"`, `"EMPTY_PATH"`

## Error Codes
- `NO_DB` — no database connection
- `NO_SERVICE` — history_query_service not available
- `NO_PLAYBACK` — no playback service or action registry
- `INVALID_ID` — invalid event_id
- `EMPTY_PATH` — empty export filepath

## States
- None explicit; `dataChanged` signals any state change

## Lifecycle
- Created by `BridgeFactory.create_history_bridge()` with db, optional services
- Creates `HistoryListModel` internally, passing db/hqs/qe
- `setPlaybackBridge(bridge)` can be called after construction to wire playback bridge

## Behavior When Service Is Null/Missing
- Without `history_query_service`: falls back to direct DB queries when `db` available
- Without `db`: history operations return `"NO_DB"`
- Without `playback_service`: `playHistoryItem` falls back to action_registry

## Integration
- **JobService**: Not used
- **ActionRegistry**: Fallback for `playHistoryItem`
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `history` bridge with no explicit capability gate

## Cancellation Contract
- `cancelExport()` removes partially written export file
- No generation counter; single export at a time

## Destructive Action Handling
- `removeHistoryItem`, `removeHistoryEvent` — irreversible single deletions
- `clearHistory()` — irreversible bulk deletion
- `applyRetention()` — irreversible automatic policy-based deletion
- `setHistoryEnabled(false)` — suspends recording (not destructive)
