# Library Bridge Contract

## Context Property
`LibraryBridge` registered as `library` context property.

## Class Name
`LibraryBridge` (`ui_qml_bridge/library_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `db` | `Any (LibraryDB) \| None` | `None` |
| `search_engine` | `Any \| None` | `None` |
| `playback_ctrl` | `Any \| None` | `None` |
| `query_service` | `Any (QueryService) \| None` | `None` |
| `query_executor` | `Any \| None` | `None` |
| `worker_manager` | `WorkerManager \| None` | `None` |
| `job_bridge` | `JobBridge \| None` | `None` |
| `track_action_service` | `Any \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `state` | `str` | `stateChanged` | LibraryState enum value (INITIALIZING, READY, etc.) |
| `songCount` | `int` | `dataChanged` | Total track count from track model |
| `albumCount` | `int` | `dataChanged` | Total album count |
| `artistCount` | `int` | `dataChanged` | Total artist count |
| `totalSongs` | `int` | `dataChanged` | Alias for songCount |
| `visibleCount` | `int` | `dataChanged` | Visible track count (after filters) |
| `loadedCount` | `int` | `dataChanged` | Number of tracks loaded for pagination |
| `hasMoreSongs` | `bool` | `dataChanged` | Whether more pages are available |
| `songs` | `QVariantList` | `dataChanged` | Always empty (use models) |
| `albums` | `QVariantList` | `dataChanged` | Always empty (use models) |
| `artists` | `QVariantList` | `dataChanged` | Always empty (use models) |
| `folders` | `QVariantList` | `dataChanged` | Always empty (use models) |
| `trackModel` | `QVariant` | `dataChanged` | TrackListModel QML instance |
| `albumModel` | `QVariant` | `dataChanged` | AlbumListModel QML instance |
| `artistModel` | `QVariant` | `dataChanged` | ArtistListModel QML instance |
| `folderModel` | `QVariant` | `dataChanged` | FolderTreeModel QML instance |
| `pageSize` | `int` | `dataChanged` | Current page size (default 100) |
| `errorMessage` | `str` | `dataChanged` | Last error message |
| `activeSortKey` | `str` | `dataChanged` | Current sort column (default "title") |
| `activeSortAscending` | `bool` | `dataChanged` | Current sort direction |
| `activeFormatFilter` | `str` | `dataChanged` | Active format filter |
| `activeGenreFilter` | `str` | `dataChanged` | Active genre filter |
| `searchQuery` | `str` | `dataChanged` | Current search query |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `getSongsPage` | `page: int, pageSize: int` | `QVariantList` | Fetch a page of songs with current filters/sort |
| `loadNextPage` | — | `dict` | Increment loaded count by pageSize |
| `setPageSize` | `size: int` | `dict` | Set page size (clamped 20-500) |
| `resetPaging` | — | `dict` | Reset loaded count to pageSize |
| `setSearchQuery` | `query: str` | `dict` | Set search text and refresh |
| `clearSearch` | — | `dict` | Clear search query |
| `search` | `query: str` | `void` | Alias for setSearchQuery |
| `setFormatFilter` | `fmt: str` | `dict` | Set format filter |
| `setGenreFilter` | `genre: str` | `dict` | Set genre filter |
| `setComposerFilter` | `composer: str` | `dict` | Set composer filter |
| `setYearFilter` | `year: str` | `dict` | Set year filter |
| `filterByArtist` | `artist: str` | `dict` | Set artist filter, clear album |
| `setArtistFilter` | `artist: str` | `dict` | Alias for filterByArtist |
| `filterByAlbum` | `album_key: str` | `dict` | Set album filter |
| `setAlbumFilter` | `album_key: str` | `dict` | Alias for filterByAlbum |
| `setFolderFilter` | `folder_path: str` | `dict` | Set folder filter |
| `setFavoritesFilter` | — | `dict` | Show only favorites |
| `setUnplayedFilter` | — | `dict` | Show only unplayed |
| `setMissingFilter` | — | `dict` | Show only missing files |
| `clearFilters` | — | `dict` | Reset all filters and search |
| `sortBy` | `key: str` | `dict` | Sort by key; toggle direction if same key |
| `refresh` | `limit: int=0` | `dict` | Refresh all models via coordinator |
| `playTrackById` | `track_id: int` | `dict` | Play track by database ID |
| `play_song` | `filepath: str` | `dict` | Play song by filepath |
| `enqueueTrackById` | `track_id: int` | `dict` | Enqueue track by ID |
| `playNextTrackById` | `track_id: int` | `dict` | Play track next |
| `addTrackToPlaylistById` | `track_id: int, playlist_id: int` | `dict` | Add track to playlist |
| `revealTrackById` | `track_id: int` | `dict` | Open file manager at track location |
| `toggleFavoriteById` | `track_id: int` | `dict` | Toggle favorite status for track |
| `enqueueSong` | `filepath: str` | `dict` | Enqueue a song by filepath |
| `revealInFileManager` | `filepath: str` | `dict` | Open file manager at file location |
| `getAlbumDetail` | `album_key: str` | `dict` | Get album metadata |
| `getAlbumTracks` | `album_key: str` | `QVariantList` | Get tracks for an album |
| `playAlbum` | `album_key: str` | `dict` | Play an entire album |
| `enqueueAlbum` | `album_key: str` | `dict` | Enqueue an album |
| `getArtistDetail` | `artist_name: str` | `dict` | Get artist metadata |
| `getArtistTracks` | `artist_name: str` | `QVariantList` | Get tracks for an artist |
| `getArtistAlbums` | `artist_name: str` | `QVariantList` | Get album keys for an artist |
| `playArtist` | `artist_name: str` | `dict` | Play all tracks by artist |
| `getFolderTracks` | `folder_path: str` | `QVariantList` | Get tracks in a folder |
| `filterByFolder` | `folder_path: str` | `dict` | Set folder filter |
| `playFolder` | `folder_path: str` | `dict` | Play all tracks in folder |
| `openFolder` | `folder_path: str` | `dict` | Open folder in system file manager |
| `addFolder` | `folder_path: str` | `dict` | Add folder as library source and scan |
| `getMusicFolder` | — | `str` | Get configured music folder path |
| `setMusicFolder` | `folder_path: str` | `dict` | Set music folder in settings |
| `scanMusicFolder` | — | `dict` | Scan default music folder |
| `addMedia` | `path: str` | `dict` | Add media path (file or folder) and scan |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Display data changed (counts, filters, page) |
| `stateChanged` | — | Library state machine transition |

## Models Exposed
| Model | Purpose |
|-------|---------|
| `TrackListModel` | QML track list with pagination |
| `AlbumListModel` | QML album grid |
| `ArtistListModel` | QML artist list |
| `FolderTreeModel` | QML folder tree |

## LibraryState Enum Values
INITIALIZING, NO_SOURCES, SOURCE_EMPTY, SOURCE_OFFLINE, SOURCE_PERMISSION_ERROR, SCANNING, INDEXING, LOADING, READY, FILTERED_EMPTY, DATABASE_ERROR, QUERY_ERROR, PARTIAL_RESULTS, CANCELLED, MISSING_CONTENT

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"NOT_FOUND"`, `"NO_QUERY_SERVICE"`, `"NO_PLAYER_SERVICE"`, `"NO_JOB_SERVICE"`, `"NO_PLAY_METHOD"`, `"FILE_NOT_FOUND"`, `"EMPTY_FILEPATH"`, `"DIR_NOT_FOUND"`, `"NO_VALID_TRACKS"`, `"NO_TRACKS"`, `"NO_DB"`, `"UNSUPPORTED"`, `"PLAYBACK_ERROR"`, `"MUSIC_FOLDER_NOT_FOUND"`

## States
- `LibraryState` enum governs `state` property
- Transition via `_state` attribute (initially INITIALIZING)
- Filter booleans: _filter_favorites, _filter_unplayed, _filter_missing

## Lifecycle
- Created by `BridgeFactory.create_library_bridge()` with db, worker_manager, playback_ctrl
- Creates 4 QML models and `LibraryRefreshCoordinator` internally
- `LibraryRefreshCoordinator` orchestrates coordinated refresh across all models
- `_wire_job_bridge_library()` called after creation to link library coordinator with job bridge
- Pagination: `_page_size` (default 100), `_loaded_count` tracks visible progress

## Behavior When Service Is Null/Missing
- Without `query_service`: `getSongsPage` returns empty, model queries fail
- Without `playback_ctrl`: play/enqueue operations return `"NO_PLAYER_SERVICE"`
- Without `job_bridge`: `addFolder`, `addMedia`, `scanMusicFolder` return `"NO_JOB_SERVICE"`
- Without `db`: `toggleFavoriteById`, `addFolder` fail
- Without `tas` (track_action_service): `playTrackById` falls back to query_svc

## Integration
- **JobService**: `addFolder` creates a `library_scan` job via job_bridge
- **ActionRegistry**: Not directly used
- **NavigationBridge**: Not directly used
- **CapabilityBridge**: Registered as `library` capability; requires `db`

## Cancellation Contract
- No explicit cancellation in library bridge
- `LibraryRefreshCoordinator` handles refresh dedup internally
- Stale pagination not guarded by generation counter

## Destructive Action Handling
- `toggleFavoriteById` — toggles favorite flag (reversible)
- `addFolder`, `addMedia` — adds to library sources (additive, reversible via source management)
- No track deletion or library clearing in bridge
