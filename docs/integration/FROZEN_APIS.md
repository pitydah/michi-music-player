# FROZEN APIS — Domain Parity Contract

**Date:** 2026-07-14
**Status:** FROZEN — do not modify without updating all consumers

---

## Bridge Constructors

| Bridge | Constructor Signature |
|---|---|
| NavigationBridge | `NavigationBridge(parent=None)` |
| HomeBridge | `HomeBridge(parent=None)` |
| LibraryBridge | `LibraryBridge(query_service, query_executor=None)` |
| QueueBridge | `QueueBridge(parent=None)` |
| HistoryBridge | `HistoryBridge(parent=None)` |
| SettingsBridgeV2 | `SettingsBridgeV2(parent=None)` |
| MetadataBridge | `MetadataBridge(parent=None)` |
| MichiAIBridge | `MichiAIBridge(ai_controller, context_service, plan_builder, tool_registry, action_registry, navigation_bridge, track_action_service, playlist_service, global_search_service, settings_service, diagnostics_service, worker_manager)` |
| LibraryDoctorBridge | `LibraryDoctorBridge(parent=None)` |
| PlaylistsBridge | `PlaylistsBridge(parent=None)` |
| SettingsBridge | `SettingsBridge(parent=None)` |

## Context Names

| Name | Bridge |
|---|---|
| navigationBridge | NavigationBridge |
| routeRegistryBridge | RouteRegistryBridge |
| homeBridge | HomeBridge |
| libraryBridge | LibraryBridge |
| queueBridge | QueueBridge |
| historyBridge | HistoryBridge |
| settingsBridgeV2 | SettingsBridgeV2 |
| settingsBridge | SettingsBridge (legacy/fallback) |
| metadataBridge | MetadataBridge |
| michiAIBridge | MichiAIBridge |
| libraryDoctorBridge | LibraryDoctorBridge |
| playlistsBridge | PlaylistsBridge |
| outputProfilesBridge | OutputProfilesBridge |
| lyricsBridge | LyricsBridge |
| smartTaggingBridge | SmartTaggingBridge |
| diagnosticsBridge | DiagnosticsBridge |
| commandPaletteBridge | CommandPaletteBridge |
| nowplayingBridge | NowPlayingBridge |
| playbackBridge | PlaybackBridge |
| notificationBridge | NotificationBridge |
| actionRegistry | ActionRegistry |
| selectionContextBridge | SelectionController |
| eqBridge | EqBridge |
| themeBridge | ThemeBridge |
| accessibilityBridge | AccessibilityBridge |

## Route IDs

| Route ID | Page Component |
|---|---|
| home | HomePage.qml |
| library | LibraryPage.qml |
| library.albums | AlbumGridPage.qml |
| library.album_detail | AlbumDetailPage.qml |
| library.artists | ArtistGridPage.qml |
| library.artist_detail | ArtistDetailPage.qml |
| library.folders | FolderBrowserPage.qml |
| library.sources | SourcesPage.qml |
| queue | QueuePage.qml |
| nowplaying | NowPlayingPage.qml |
| playback | PlaybackPage.qml |
| playlists | PlaylistsPage.qml |
| playlist_detail | PlaylistDetailPage.qml |
| history | HistoryPage.qml |
| settings | SettingsPage.qml |
| settings.general | SettingsGeneralPage.qml |
| settings.appearance | SettingsAppearancePage.qml |
| settings.playback | SettingsPlaybackPage.qml |
| settings.library | SettingsLibraryPage.qml |
| settings.accessibility | SettingsAccessibilityPage.qml |
| settings.audio | SettingsAudioPage.qml |
| settings.about | SettingsAboutPage.qml |
| outputs | OutputProfilesPage.qml |
| lyrics | LyricsPage.qml |
| metadata.inspector | MetadataInspectorPage.qml |
| metadata.batch | MetadataBatchEditor.qml |
| tagging | SmartTaggingPage.qml |
| library_doctor | LibraryDoctorPage.qml |
| diagnostics | DiagnosticsPage.qml |
| command_palette | CommandPalette.qml |
| michi_ai | AssistantPage.qml |
| assistant | AssistantPage.qml (alias) |
| shell | AppShell.qml |

## Shared Component APIs

| Component | Key Properties | Key Signals | Key Slots |
|---|---|---|---|
| MichiButton | text, variant, enabled, objectName | clicked | — |
| GlassMaterial | radius, variant, hovered, interactive, objectName | — | — |
| StatusBadge | text, kind, objectName | — | — |
| SectionHeader | text, objectName | — | — |
| SearchField | placeholderText, objectName | searchTextChanged | — |
| MichiProgressBar | value, indeterminate, objectName | — | — |
| LoadingState | title, message, objectName | — | — |
| EmptyState | title, subtitle, iconText, actionText, objectName | actionClicked | — |
| ErrorState | title, message, retryText, objectName | retryRequested | — |
| UnavailableState | title, message, explanation, objectName | — | — |
| CancellationState | title, message, objectName | — | — |
| ConfirmActionDialog | title, message, objectName | confirmed, rejected | open, close |
| HeroMaterial | width, height, radius, showGlow | — | — |
| GlassCard | width, height, title, subtitle, objectName | clicked | — |
| SettingsRow | entry, objectName | clicked | — |
| FocusScope | activeFocusOnTab, objectName | — | forceActiveFocus |

## Model Roles (standard)

| Model | Roles |
|---|---|
| LibraryTrackModel | track_id, track_uid, title, artist, album, album_key, duration, format, year, genre, track_number, favorite, missing, cover_key, filepath, disc_number, bit_depth |
| AlbumListModel | album_key, title, artist, year, cover_key, track_count |
| ArtistListModel | name, album_count, track_count |
| FolderTreeModel | path, name, type, children |
| QueueListModel | id, title, artist, album, duration, cover_key |
| HistoryListModel | eventId, trackId, title, artist, album, playedAt, device |

## ObjectName Convention

**Pattern:** `page.section.control`

Examples:
- `home.page` — root page
- `home.playbackCard` — section card
- `home.continueButton` — control
- `library.page` — root page
- `library.navBar` — section
- `library.trackTable` — control
- `history.toolbar.clearAll` — section.control
- `settings.audio.outputDevice` — section.control
- `playlist.detail.playAll` — section.control

## Error Codes

| Code | Meaning |
|---|---|
| UNKNOWN_ACTION:{action} | Bridge received unrecognized action |
| BACKEND_ERROR:{detail} | Backend service failure |
| STALE_CALLBACK:{detail} | Stale callback detected (load_counter mismatch) |
| SERVICE_UNAVAILABLE | Bridge not configured |
| DATABASE_ERROR | SQLite operation failed |
| QUERY_ERROR | Library query failed |
| NOT_IMPLEMENTED | Action not yet implemented |
| VALIDATION_ERROR:{detail} | Input validation failure |
| CANCELLED | Operation cancelled by user |
| REJECTED | User rejected confirmation dialog |

## Job Interactions

| Operation | Bridge Method | Result Shape |
|---|---|---|
| Scan library | `LibraryDoctorBridge.scan()` | `{"ok": bool, "issues": [...]}` |
| Dry run repair | `LibraryDoctorBridge.dryRun()` | `{"ok": bool, "preview": str}` |
| Execute repair | `LibraryDoctorBridge.repair()` | `{"ok": bool, "fixed": int}` |
| Cancel operation | `LibraryDoctorBridge.cancelScan()` | `{"ok": bool}` |
| Create playlist | `PlaylistsBridge.create(name)` | `{"ok": bool, "id": int}` |
| Add tracks | `PlaylistsBridge.addTracks(pid, tids)` | `{"ok": bool}` |
| Reorder playlist | `PlaylistsBridge.reorder(pid, from, to)` | `{"ok": bool}` |
| Export playlist | `PlaylistsBridge.export(pid)` | `{"ok": bool, "path": str}` |
| Reorder queue | `QueueBridge.moveItem(from, to)` | `{"ok": bool}` |
| Undo queue | `QueueBridge.undo()` | `{"ok": bool}` |
| Apply metadata | `MetadataBridge.applyChanges(t, a, al)` | `{"ok": bool}` |
| AI send message | `MichiAIBridge.sendMessage(msg)` | status transitions: idle → executing → completed/failed/cancelled/awaiting_confirmation |
| AI cancel | `MichiAIBridge.cancel()` | status → cancelled |
| Set value | `SettingsBridgeV2.setValue(k, v)` | `{"ok": bool, "requires_restart": bool}` |
| Reset all | `SettingsBridgeV2.resetAll()` | `{"ok": bool}` |
