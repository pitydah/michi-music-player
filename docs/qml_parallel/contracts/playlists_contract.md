# PlaylistsBridge Integration Contract
# Playlists Bridge Contract

## Context Property
- `playlistsBridge` → `PlaylistsBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `playlists` | `QVariantList` | `dataChanged` |

Playlist schema: `{id: int, title: str, track_count: int, duration: str, cover_key: str, is_smart: bool, updated_at: str, description: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `createPlaylist` | `dict` | `name: str` |
| `deletePlaylist` | `dict` | `pid: int` |
| `renamePlaylist` | `dict` | `pid: int`, `name: str` |
| `getPlaylistDetail` | `dict` | `pid: int` |
| `addTrackToPlaylist` | `dict` | `pid: int`, `filepath: str = ""`, `track_id: str = ""` |
| `removeTrackFromPlaylist` | `dict` | `pid: int`, `track_id: int` |
| `addSelectedTrackToPlaylist` | `dict` | `pid: int` |
| `batchAddTracks` | `dict` | `pid: int`, `tracks: list` |
| `batchAddTrackIds` | `dict` | `playlist_id: int`, `track_ids: list` |
| `duplicatePlaylist` | `dict` | `pid: int` |
| `clearPlaylist` | `dict` | `pid: int` |
| `reorderTrack` | `dict` | `pid: int`, `from_index: int`, `to_index: int` |
| `playPlaylistFromIndex` | `dict` | `pid: int`, `index: int = 0` |
| `playPlaylist` | `dict` | `pid: int` |
| `saveQueueAsPlaylist` | `dict` | `name: str` |
| `previewPlaylistImport` | `dict` | `filepath: str` |
| `confirmPlaylistImport` | `dict` | `filepath: str`, `name: str = ""` |
| `cancelPlaylistImport` | `dict` | `import_id: str` |
| `importM3U` | `dict` | `filepath: str` |
| `importM3U8` | `dict` | `filepath: str` |
| `exportM3U` | `dict` | `playlist_id: int`, `destination_path: str` |
| `exportM3U8` | `dict` | `playlist_id: int`, `destination_path: str` |
| `playlistScore` | `dict` | none |

Most slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"NO_DB"` — no DB connection or get_playlists not available
- `"NO_SERVICE"` — playlist service not injected
- `"NO_SELECTION"` — no track selected via SelectionController
- `"NO_VALID_TRACK"` — no valid track identifier
- `"NO_TRACKS"` — playlist is empty
- `"EMPTY_NAME"` — name is empty
- `"UNSUPPORTED"` — reorder not available

## Lifecycle Expectations
- Constructor takes optional `db`, `selection_context`, `player_service`, `playlist_service`.
- `_can()` returns True if `_svc` is available OR `_db` has `get_playlists`.
- Demo data only shown when `MICHI_QML_DEMO=1` env var set and no real playlists.

## Behavior When Service Is Missing/Null
- No `_svc`: CRUD delegates to `_db` methods (`create_playlist`, `delete_playlist`, `update_playlist`). `previewPlaylistImport`/`confirmPlaylistImport`/`exportM3U` return `NO_SERVICE`.
- No `_db`: `_can()` returns False. Most operations return `NO_DB`.

## Destructive Actions and Confirmations
- `deletePlaylist(pid)` — deletes a playlist. No confirmation in bridge.
- `clearPlaylist(pid)` — removes all tracks from playlist. No confirmation.
- `removeTrackFromPlaylist(pid, track_id)` — removes track. No confirmation.

## Cancellation Contract
- `cancelPlaylistImport(import_id)`: delegates to `_svc.import_cancel(import_id)` if available. Returns `{ok: true}` as no-op fallback.

## Destructive Action Handling
- `deletePlaylist(pid)` — permanent deletion
- `clearPlaylist(pid)` — removes all tracks but keeps playlist
- `removeTrackFromPlaylist(pid, track_id)` — removes single track
- `duplicatePlaylist(pid)` — creates new playlist (additive, not destructive)
- No undo available for any destructive operation
# PlaylistsBridge Integration Contract

## Context Property
- `playlistsBridge` → `PlaylistsBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `playlists` | `QVariantList` | `dataChanged` |

Playlist schema: `{id: int, title: str, track_count: int, duration: str, cover_key: str, is_smart: bool, updated_at: str, description: str}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `refresh` | (none) | none |
| `createPlaylist` | `dict` | `name: str` |
| `deletePlaylist` | `dict` | `pid: int` |
| `renamePlaylist` | `dict` | `pid: int`, `name: str` |
| `getPlaylistDetail` | `dict` | `pid: int` |
| `addTrackToPlaylist` | `dict` | `pid: int`, `filepath: str = ""`, `track_id: str = ""` |
| `removeTrackFromPlaylist` | `dict` | `pid: int`, `track_id: int` |
| `addSelectedTrackToPlaylist` | `dict` | `pid: int` |
| `batchAddTracks` | `dict` | `pid: int`, `tracks: list` |
| `batchAddTrackIds` | `dict` | `playlist_id: int`, `track_ids: list` |
| `duplicatePlaylist` | `dict` | `pid: int` |
| `clearPlaylist` | `dict` | `pid: int` |
| `reorderTrack` | `dict` | `pid: int`, `from_index: int`, `to_index: int` |
| `playPlaylistFromIndex` | `dict` | `pid: int`, `index: int = 0` |
| `playPlaylist` | `dict` | `pid: int` |
| `saveQueueAsPlaylist` | `dict` | `name: str` |
| `previewPlaylistImport` | `dict` | `filepath: str` |
| `confirmPlaylistImport` | `dict` | `filepath: str`, `name: str = ""` |
| `cancelPlaylistImport` | `dict` | `import_id: str` |
| `importM3U` | `dict` | `filepath: str` |
| `importM3U8` | `dict` | `filepath: str` |
| `exportM3U` | `dict` | `playlist_id: int`, `destination_path: str` |
| `exportM3U8` | `dict` | `playlist_id: int`, `destination_path: str` |
| `playlistScore` | `dict` | none |

Most slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `dataChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"NO_DB"` — no DB connection or get_playlists not available
- `"NO_SERVICE"` — playlist service not injected
- `"NO_SELECTION"` — no track selected via SelectionController
- `"NO_VALID_TRACK"` — no valid track identifier
- `"NO_TRACKS"` — playlist is empty
- `"EMPTY_NAME"` — name is empty
- `"UNSUPPORTED"` — reorder not available

## Lifecycle Expectations
- Constructor takes optional `db`, `selection_context`, `player_service`, `playlist_service`.
- `_can()` returns True if `_svc` is available OR `_db` has `get_playlists`.
- Demo data only shown when `MICHI_QML_DEMO=1` env var set and no real playlists.

## Behavior When Service Is Missing/Null
- No `_svc`: CRUD delegates to `_db` methods (`create_playlist`, `delete_playlist`, `update_playlist`). `previewPlaylistImport`/`confirmPlaylistImport`/`exportM3U` return `NO_SERVICE`.
- No `_db`: `_can()` returns False. Most operations return `NO_DB`.

## Destructive Actions and Confirmations
- `deletePlaylist(pid)` — deletes a playlist. No confirmation in bridge.
- `clearPlaylist(pid)` — removes all tracks from playlist. No confirmation.
- `removeTrackFromPlaylist(pid, track_id)` — removes track. No confirmation.

## Cancellation Contract
- `cancelPlaylistImport(import_id)`: delegates to `_svc.import_cancel(import_id)` if available. Returns `{ok: true}` as no-op fallback.

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
