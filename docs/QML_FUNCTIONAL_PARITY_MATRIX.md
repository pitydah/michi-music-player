# QML Functional Parity Matrix

**Legend:** ✅ Full parity · ⚠️ Partial · ❌ Missing · — Not applicable

## Library

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Track list with pagination | ✅ | ✅ | QML uses TrackListModel (async) |
| Album grid | ✅ | ✅ | AlbumListModel + AlbumGrid.qml |
| Artist list | ✅ | ✅ | ArtistListModel + ArtistList.qml |
| Folder browser | ✅ | ✅ | FolderTreeModel + FolderBrowser.qml |
| Search with FTS5 | ✅ | ✅ | FTS5 + LIKE fallback |
| Filters (artist, album, format) | ✅ | ✅ | Via LibraryQueryService |
| Sort by column | ✅ | ✅ | Via QuerySort |
| Song context menu | ✅ | ⚠️ | SelectionContextBridge exists, menu pending |
| Multi-select | ✅ | ❌ | Not implemented in QML |

## Playback

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Play/pause/next/prev | ✅ | ✅ | PlaybackBridge |
| Volume control | ✅ | ✅ | playbackBridge.volumeUp/Down |
| Seek | ✅ | ✅ | playbackBridge.seekForward/Backward |
| Queue display | ✅ | ✅ | QueueListModel + QueueBridge |
| Queue reorder | ✅ | ⚠️ | moveItem exists, drag UI pending |
| Now playing bar | ✅ | ✅ | NowPlayingBridge |
| Cover art | ✅ | ✅ | CoverBridge (QQuickPaintedItem) |

## Playlists

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Create/rename/delete | ✅ | ✅ | PlaylistsBridge |
| Add/remove tracks | ✅ | ✅ | By ID or filepath |
| Batch add by ID | ✅ | ✅ | batchAddTrackIds |
| Duplicate | ✅ | ✅ | duplicatePlaylist |
| Import M3U/M3U8 | ✅ | ✅ | importM3U, importM3U8 |
| Export M3U | ✅ | ✅ | exportM3U(playlist_id, path) |
| Play from index | ✅ | ✅ | playPlaylistFromIndex |
| Preview import | ❌ | ❌ | Not implemented |

## Queue & History

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Queue display | ✅ | ✅ | QueueListModel |
| Play from queue | ✅ | ✅ | playFromIndex |
| Remove from queue | ✅ | ✅ | removeFromQueue |
| Clear queue | ✅ | ✅ | clearQueue |
| Move item | ✅ | ✅ | moveItem |
| Save as playlist | ✅ | ✅ | saveAsPlaylist |
| History display | ✅ | ✅ | HistoryListModel |
| Clear history | ✅ | ✅ | clearHistory |
| Play from history | ✅ | ✅ | Via HistoryBridge |
| Privacy mode | ✅ | ❌ | Not implemented in QML |

## Radio

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| List stations | ✅ | ✅ | RadioBridge.stations |
| Add station | ✅ | ✅ | addStation |
| Delete station | ✅ | ✅ | deleteStation |
| Edit station | ✅ | ✅ | editStation |
| Play station | ✅ | ✅ | playStation |
| Favorites | ✅ | ✅ | toggleFavorite |
| Search by name/country/tag | ✅ | ✅ | search() |

## Lyrics

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Synced lyrics display | ✅ | ✅ | LyricsBridge |
| Auto-scroll | ✅ | ✅ | getActiveLine |
| Manual search | ✅ | ✅ | searchManual |
| Cache | ✅ | ✅ | LRU cache in bridge |
| Offline | ✅ | ✅ | Cache serves offline |

## Mix

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Favorites mix | ✅ | ✅ | loadMix('favorites') |
| Recent mix | ✅ | ✅ | loadMix('recent') |
| Most played | ✅ | ✅ | loadMix('most_played') |
| Unplayed | ✅ | ✅ | loadMix('unplayed') |
| Daily mix | ✅ | ✅ | loadMix('daily_mix') |
| AI recommended | ✅ | ✅ | loadMix('ai_recommended') |

## Jobs

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Job list | ✅ | ✅ | JobBridge.jobs |
| Active count | ✅ | ✅ | JobBridge.activeCount |
| Cancel job | ✅ | ✅ | cancelJob |
| Retry job | ✅ | ❌ | retryJob exists but no UI |
| Clear completed | ✅ | ✅ | clearCompleted |
| Status banner | ✅ | ✅ | JobStatusBanner.qml |

## System

| Feature | QtWidgets | QML | Notes |
|---|---|---|---|
| Navigation | ✅ | ✅ | NavigationBridge |
| Command palette | ✅ | ✅ | CommandPaletteBridge |
| Global search | ✅ | ✅ | GlobalSearchBridge |
| Settings | ✅ | ⚠️ | Partial (EQ, audio lab migrated) |
| Library sources | ✅ | ✅ | LibrarySourcesPage.qml |
| Library doctor | ✅ | ⚠️ | Doctor bridge exists, UI pending |
| Diagnostics | ✅ | ✅ | DiagnosticsBridge |
| Disc detection | ✅ | ✅ | DiscLabBridge |
| Michi AI | ✅ | ✅ | MichiAIBridge |
