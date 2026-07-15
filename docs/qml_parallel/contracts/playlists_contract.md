# Playlists Bridge Contract

## Context Property
`PlaylistsBridge` registered as `playlists` context property.

## Class Name
`PlaylistsBridge` (`ui_qml_bridge/playlists_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db` | `Any (LibraryDB) \| None` | `None` |
| `selection_context` | `SelectionContext \| None` | `None` |
| `player_service` | `Any \| None` | `None` |
| `playlist_service` | `Any (PlaylistService) \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `playlists` | `QVariantList` | `dataChanged` | List of playlist dicts with id, title, track_count, duration, cover_key, is_smart, updated_at, description |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `void` | Reload all playlists from DB |
| `createPlaylist` | `name: str` | `dict` | Create a new playlist; returns id |
| `deletePlaylist` | `pid: int` | `dict` | Delete a playlist |
| `renamePlaylist` | `pid: int, name: str` | `dict` | Rename a playlist |
| `getPlaylistDetail` | `pid: int` | `dict` | Get tracks for a playlist |
| `addTrackToPlaylist` | `pid: int, filepath: str="", track_id: str=""` | `dict` | Add track by filepath or track_id; falls back to selection context |
| `removeTrackFromPlaylist` | `pid: int, track_id: int` | `dict` | Remove a track from a playlist |
| `addSelectedTrackToPlaylist` | `pid: int` | `dict` | Add currently selected track to playlist |
| `batchAddTracks` | `pid: int, tracks: list` | `dict` | Batch add tracks from list of dicts |
| `batchAddTrackIds` | `playlist_id: int, track_ids: list` | `dict` | Batch add tracks by ID list |
| `duplicatePlaylist` | `pid: int` | `dict` | Duplicate a playlist with "(copia)" suffix |
| `clearPlaylist` | `pid: int` | `dict` | Remove all tracks from a playlist |
| `reorderTrack` | `pid: int, from_index: int, to_index: int` | `dict` | Reorder track within playlist |
| `playPlaylistFromIndex` | `pid: int, index: int=0` | `dict` | Play playlist starting at index |
| `playPlaylist` | `pid: int` | `dict` | Play entire playlist |
| `saveQueueAsPlaylist` | `name: str` | `dict` | Save current playback queue as playlist |
| `previewPlaylistImport` | `filepath: str` | `dict` | Preview M3U/PLS import |
| `confirmPlaylistImport` | `filepath: str, name: str=""` | `dict` | Confirm and execute import |
| `cancelPlaylistImport` | `import_id: str` | `dict` | Cancel pending import |
| `importM3U` | `filepath: str` | `dict` | Import M3U playlist file |
| `importM3U8` | `filepath: str` | `dict` | Import M3U8 playlist file |
| `exportM3U` | `playlist_id: int, destination_path: str` | `dict` | Export playlist as M3U |
| `exportM3U8` | `playlist_id: int, destination_path: str` | `dict` | Export playlist as M3U8 |
| `playlistScore` | — | `dict` | Return capability score (0-100) with sub-metrics |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Playlist list changed |

## Models Exposed
None. Playlists and tracks returned as dicts/lists.

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"NO_DB"`, `"NO_SERVICE"`, `"NO_SELECTION"`, `"NO_VALID_TRACK"`, `"NO_TRACKS"`, `"EMPTY_NAME"`, `"UNSUPPORTED"`

## Error Codes
- `NO_DB` — no database or playlist service
- `NO_SERVICE` — playlist_service not available
- `NO_SELECTION` — no selection context for adding tracks
- `NO_VALID_TRACK` — filepath invalid or track_id non-numeric
- `NO_TRACKS` — playlist is empty
- `EMPTY_NAME` — playlist name is empty
- `UNSUPPORTED` — operation not supported by backend
- `NO_TRACKS` — enqueue source has no tracks

## States
- None explicit; `dataChanged` on any mutation

## Lifecycle
- Created by `BridgeFactory.create_playlists_bridge()` with db + player_service
- `setSelectionContext(ctx)` can be called after construction
- Demo mode (MICHI_QML_DEMO=1) shows fake playlists when DB unavailable
- `refresh()` must be called explicitly to populate initial data

## Behavior When Service Is Null/Missing
- Without `db`: `_can()` returns False, operations return `"NO_DB"`
- Without `playlist_service`: falls back to `_db` methods (create, delete, update)
- Without `player_service`: `playPlaylist`, `playPlaylistFromIndex`, `saveQueueAsPlaylist` fail
- Without `selection_context`: `addTrackToPlaylist` requires explicit filepath/track_id

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `playlists` capability; requires `db`

## Cancellation Contract
- `cancelPlaylistImport(import_id)` cancels pending import
- No generation counter; single import at a time

## Destructive Action Handling
- `deletePlaylist(pid)` — permanent deletion
- `clearPlaylist(pid)` — removes all tracks but keeps playlist
- `removeTrackFromPlaylist(pid, track_id)` — removes single track
- `duplicatePlaylist(pid)` — creates new playlist (additive, not destructive)
- No undo available for any destructive operation
