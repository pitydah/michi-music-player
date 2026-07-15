# QML Domain Public Contract — Final State

**Date:** 2026-07-14
**Status key:** `STATIC` (shell-only), `PARTIAL` (page exists partially), `FUNCTIONAL` (page renders with real bridge), `PRODUCTIVE` (fully integrated), `PARITY_READY` (equals QtWidgets).

---

## Routes owned by this domain

| Route | Page | Bridge | Models | Primary Actions | Secondary Actions | Errors | Loading | Empty | Keyboard | Accessibility | Persistence | Legacy Equivalent | Missing Integration |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **home** | HomePage.qml | HomeBridge | — | ContinuePlayback, ResumeQueue, ReconnectServer, OpenJobs, OpenSource, OpenAssistant | Playback card actions | ErrorState (bridge not found, refresh failed) | LoadingState | EmptyState (add music) | FocusScope, Keys.onEscapePressed, KeyNavigation.tab chains | Accessible Panel "Inicio", named cards | None | HomePage (QtWidgets) | None |
| **library** | LibraryPage.qml | LibraryBridge | LibraryTrackModel, albumModel, artistModel, folderModel | Search, filter, tab switch, play track, navigate to album/artist/folder detail | Source management | LibraryErrorState (DB/query), UnavailableState | BusyIndicator | LibraryEmptyState (no sources, filtered empty) | FocusScope, Keys.onEscapePressed (clear filters), KeyNavigation.tab chains | Panel "Biblioteca", named sections, accessible list items | None | LibraryPage (QtWidgets) | None |
| **library.albums** | AlbumGridPage.qml | LibraryBridge (albumModel) | AlbumListModel, AlbumPagedListModel | Click album → AlbumDetailPage | — | — | — | — | — | — | None | AlbumView (QtWidgets) | Dedicated bridge |
| **library.album_detail** | AlbumDetailPage.qml | LibraryBridge | — | Play, shuffle, queue album, add to playlist | Disc filter, track click | Inline error text | BusyIndicator | — | Keys.onEscapePressed (back), KeyNavigation chains | Panel "Detalle del álbum", accessible track rows | None | AlbumDetailWidget | Dedicated bridge |
| **library.artists** | ArtistGridPage.qml | LibraryBridge (artistModel) | ArtistListModel | Click artist → ArtistDetailPage | — | — | — | — | — | — | None | ArtistView (QtWidgets) | Dedicated bridge |
| **library.artist_detail** | ArtistDetailPage.qml | LibraryBridge | — | Play all, shuffle, enqueue, go to Mix | Album click, track click | Inline error text | BusyIndicator | — | Keys.onEscapePressed (back), KeyNavigation chains | Panel "Detalle del artista", accessible album/track rows | None | ArtistDetailWidget | Dedicated bridge |
| **library.folders** | FolderBrowserPage.qml | LibraryBridge (folderModel) | FolderTreeModel | Navigate folder tree, click track | — | — | — | — | — | — | None | FolderBrowser (QtWidgets) | Dedicated bridge |
| **library.sources** | SourcesPage.qml | LibraryBridge / LibrarySourcesBridge | — | Add, scan, edit, remove sources | — | Inline error | — | — | — | — | Source config (via bridge) | SourcesPage (QtWidgets) | Dedicated bridge |
| **queue** | QueuePage.qml | QueueBridge | QueueListModel | Reorder, remove, clear, play from queue | History section | — | — | QueueEmptyState | FocusScope, KeyNavigation | Accessible Panel | QueueState persisted (JSON) | QueuePage (QtWidgets) | None |
| **nowplaying** | NowPlayingPage.qml (via playback page) | NowPlayingBridge / PlaybackBridge | — | Play/Pause, Prev/Next, Seek, Volume, Shuffle, Repeat | Quality badges, output selector | Error banner (inline) | — | — | — | — | Volume, playback state | NowPlayingPage (QtWidgets) | None |
| **playback** | PlaybackPage.qml | PlaybackBridge / NowPlayingBridge | — | Play/Pause, Prev/Next, Seek, Volume, Shuffle, Repeat | Queue preview, history preview, navigate lyrics/metadata | Error banner (inline) | — | — | — | — | Volume, playback state | NowPlayingPage (QtWidgets) | None |
| **playlists** | PlaylistsPage.qml | PlaylistsBridge | — | Create, import, smart playlist, duplicate, select, delete | Search | UnavailableState, inline status text | LoadingState | EmptyState | FocusScope, KeyNavigation chains, Keys.onEscapePressed | Panel "Playlists", named buttons, accessible list | Playlist CRUD (via bridge) | PlaylistsPage (QtWidgets) | None |
| **playlist_detail** | PlaylistDetailPage.qml | PlaylistsBridge | — | Play, shuffle, edit, delete playlist | Track add/remove | — | — | — | — | — | Playlist data (via bridge) | PlaylistDetailWidget | Dedicated integration |
| **history** | HistoryPage.qml | HistoryBridge | HistoryListModel | Play from history, queue, remove, clear, export, filter | Timeline/Table view toggle, retention config | ErrorState | LoadingState | EmptyState | FocusScope, Keys.onEscapePressed, KeyNavigation chains, pagination | Panel "Historial", accessible items, status bar | History DB (via bridge) | HistoryPage (QtWidgets) | None |
| **settings** | SettingsPage.qml | SettingsBridgeV2 / SettingsBridge | — | Browse categories, search, open section/entry, reset | — | — | — | — | — | — | Settings DB (via bridge) | SettingsPage (QtWidgets) | None |
| **settings.general** | SettingsGeneralPage.qml | SettingsBridge | — | Edit general settings | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.appearance** | SettingsAppearancePage.qml | SettingsBridge + ThemeBridge | — | Theme, accent color | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.playback** | SettingsPlaybackPage.qml | SettingsBridge | — | Playback settings | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.library** | SettingsLibraryPage.qml | SettingsBridge | — | Library settings | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.accessibility** | SettingsAccessibilityPage.qml | SettingsBridge + AccessibilityBridge | — | Font scale, high contrast, reduced motion | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.audio** | SettingsAudioPage.qml | SettingsBridge | — | Audio output settings | — | — | — | — | — | — | Via bridge | SettingsPage (QtWidgets) | Dedicated |
| **settings.about** | SettingsAboutPage.qml | SettingsBridge | — | App info | — | — | — | — | — | — | — | AboutDialog (QtWidgets) | Dedicated |
| **outputs** | OutputProfilesPage.qml | OutputProfilesBridge | — | Select, create, edit, duplicate, delete profiles | — | Notification (via notif bridge) | — | — | — | — | Profile config (via bridge) | Settings (QtWidgets) | Dedicated |
| **lyrics** | LyricsPage.qml | LyricsBridge | — | Search lyrics, view synced/plain, change source | — | Inline error text | Inline "Buscando..." | Inline "Not found" | — | — | — | LyricsWidget (QtWidgets) | Dedicated bridge |
| **metadata.inspector** | MetadataInspectorPage.qml | MetadataBridge | — | Inspect track metadata, edit title/artist/album | — | Inline error text | — | Empty component (select track) | — | — | — | MetadataEditor (QtWidgets) | Dedicated bridge |
| **metadata.batch** | MetadataBatchEditor.qml | MetadataBridge | — | Batch edit metadata | — | — | — | — | — | — | — | MetadataEditor (QtWidgets) | Dedicated bridge |
| **tagging** | SmartTaggingPage.qml | SmartTaggingBridge | — | Apply smart tagging rules | — | — | — | — | — | — | Tagging rules (via bridge) | SmartTagging (QtWidgets) | Dedicated bridge |
| **library_doctor** | LibraryDoctorPage.qml | LibraryDoctorBridge | — | Scan, fix issues, dry run, preview, repair | — | — | — | — | — | — | Doctor data (via bridge) | LibraryDoctor (QtWidgets) | Dedicated bridge |
| **diagnostics** | DiagnosticsPage.qml | DiagnosticsBridge | — | Run checks, refresh, copy diagnostics | — | — | — | — | — | — | — | Diagnostics (QtWidgets) | Dedicated bridge |
| **command_palette** | CommandPalette.qml | ActionRegistry / CommandPaletteBridge | — | Execute action | — | — | — | — | — | — | — | CommandPalette (QtWidgets) | Dedicated bridge |
| **michi_ai** | AssistantPage.qml | MichiAIBridge | — | Chat, contextual suggestions | — | — | — | — | — | — | Conversation history (via bridge) | Assistant (QtWidgets) | Dedicated bridge |
| **assistant** | AssistantPage.qml (alias) | MichiAIBridge | — | Chat, contextual suggestions | — | — | — | — | — | — | Conversation history (via bridge) | Assistant (QtWidgets) | Dedicated bridge |
| **shell** | AppShell.qml | NavigationBridge / RouteRegistryBridge | — | Navigate routes, sidebar | — | PlaceholderPage (invalid route) | — | — | FocusScope, Keys handlers | Accessible Panel | — | MainWindow (QtWidgets) | AppShell |

## Bridge Contracts

### NavigationBridge
- **Constructor:** QObject parent
- **Dependencies:** None
- **Properties:** currentRoute (str), canGoBack (bool), canGoForward (bool)
- **Signals:** routeChanged(route), invalidRouteError(route, message)
- **Slots:** navigate(route), navigateWithParams(route, params), back(), forward(), refreshCurrent()
- **Context name:** navigationBridge

### HomeBridge
- **Constructor:** QObject parent
- **Dependencies:** None
- **Properties:** hasPlayback (bool), libraryAlbums (int), libraryArtists (int), libraryTracks (int), sourcesCount (int), lastScan (str), activeJobs (int), currentTrackTitle (str), currentArtist (str), backend (str)
- **Signals:** dataChanged
- **Slots:** refresh()
- **Context name:** homeBridge

### LibraryBridge
- **Constructor:** query_service, query_executor
- **Dependencies:** QueryService, QueryExecutor
- **Properties:** state (str), songCount (int), albumCount (int), artistCount (int), searchQuery (str), trackModel, albumModel, artistModel, folderModel
- **Signals:** stateChanged, dataChanged
- **Slots:** search(text), clearFilters(), refresh(), playTrackById(id), enqueueTrackById(id), addMedia(path), setFormatFilter(fmt), setGenreFilter(genre), setYearFilter(year), sortBy(key)
- **Context name:** libraryBridge

### QueueBridge
- **Constructor:** QObject parent
- **Dependencies:** PlaybackController
- **Properties:** queueItems (QVariantList)
- **Signals:** dataChanged
- **Slots:** refresh(), moveItem(from, to), undo()
- **Context name:** queueBridge

### HistoryBridge
- **Constructor:** QObject parent
- **Dependencies:** HistoryQueryService, PlaybackBridge
- **Properties:** historyModel (QVariantList), historyCount (int)
- **Signals:** dataChanged
- **Slots:** refresh(), playHistoryItem(trackId), removeHistoryEvent(eventId), clearHistory()
- **Context name:** historyBridge

### SettingsBridgeV2
- **Constructor:** QObject parent
- **Dependencies:** SettingsManager
- **Properties:** categories (QVariantList)
- **Signals:** dataChanged
- **Slots:** getValue(key), setValue(key, value), resetValue(key), resetAll(), refresh()
- **Context name:** settingsBridgeV2 / settingsBridge

### MetadataBridge
- **Constructor:** QObject parent
- **Dependencies:** MetadataService
- **Properties:** trackTitle (str), trackArtist (str), trackAlbum (str), hasSelection (bool), fields (QVariantList), artworkStatus (str), qualitySummary (str), errorMessage (str)
- **Signals:** dataChanged
- **Slots:** inspectTrack(filepath), applyChanges(title, artist, album)
- **Context name:** metadataBridge

### MichiAIBridge
- **Constructor:** ai_controller, context_service, plan_builder, tool_registry, action_registry, navigation_bridge, track_action_service, playlist_service, global_search_service, settings_service, diagnostics_service, worker_manager
- **Dependencies:** Multiple services
- **Properties:** status (str), suggestions (QVariantList), chat_history (QVariantList)
- **Signals:** statusChanged
- **Slots:** sendMessage(msg), cancel(), refresh()
- **Context name:** michiAIBridge

### LibraryDoctorBridge
- **Constructor:** QObject parent
- **Dependencies:** DoctorService
- **Properties:** status (str), issues (QVariantList), totalChecked (int), issueCount (int)
- **Signals:** dataChanged
- **Slots:** refresh(), scan(), dryRun(), repair(), cancelScan(), selectAll(), selectNone(), setIssueSelected(id, selected)
- **Context name:** libraryDoctorBridge

### PlaylistsBridge
- **Constructor:** QObject parent
- **Dependencies:** PlaylistService
- **Properties:** playlists (QVariantList)
- **Signals:** dataChanged
- **Slots:** refresh(), create(name), addTracks(playlistId, trackIds), reorder(playlistId, from, to), export(playlistId)
- **Context name:** playlistsBridge

### Settings sub-page bridges
- **Context name:** settingsBridge (same object shared across sub-pages)
- **Sub-pages:** SettingsGeneralPage, SettingsAppearancePage, SettingsPlaybackPage, SettingsLibraryPage, SettingsAccessibilityPage, SettingsAudioPage, SettingsAboutPage
- **Convention:** objectName "settings.{section}"
- **Controls:** objectName "settings.{section}.{control}"

## State Assessment

| Route | State |
|---|---|
| home | PRODUCTIVE |
| library | PRODUCTIVE |
| library.albums | FUNCTIONAL |
| library.album_detail | FUNCTIONAL |
| library.artists | FUNCTIONAL |
| library.artist_detail | FUNCTIONAL |
| library.folders | FUNCTIONAL |
| library.sources | FUNCTIONAL |
| queue | PRODUCTIVE |
| nowplaying | FUNCTIONAL |
| playback | FUNCTIONAL |
| playlists | PRODUCTIVE |
| playlist_detail | FUNCTIONAL |
| history | PRODUCTIVE |
| settings | FUNCTIONAL |
| settings.general | PARTIAL |
| settings.appearance | PARTIAL |
| settings.playback | PARTIAL |
| settings.library | PARTIAL |
| settings.accessibility | PARTIAL |
| settings.audio | PARTIAL |
| settings.about | PARTIAL |
| outputs | FUNCTIONAL |
| lyrics | FUNCTIONAL |
| metadata.inspector | FUNCTIONAL |
| metadata.batch | PARTIAL |
| tagging | PARTIAL |
| library_doctor | FUNCTIONAL |
| diagnostics | FUNCTIONAL |
| command_palette | FUNCTIONAL |
| michi_ai | PRODUCTIVE |
| assistant | PRODUCTIVE (alias) |
| shell | PRODUCTIVE |

## Added Workflows
- Responsive tests at `tests/qml/responsive/`: home, library, settings, shell
- Domain workflow harness at `tests/qml/workflows_domain/domain_workflow_harness.py`
- Workflow tests: library search play, album queue, queue reorder undo, playlist create export, history filter play remove, settings rollback, metadata preview confirm, doctor scan dry run, michi_ai proposal execution, keyboard full page
- Negative tests: service unavailable, backend error, cancellation, stale callback, invalid selection, rejected confirmation
