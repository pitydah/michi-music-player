# HANDOFF — Michi QML Domain Migration Wave

## Commit References

| Field | Value |
|-------|-------|
| Initial SHA | `fbaeca33` |
| Final SHA | `34d1d0c` |
| Total commits | 367 |

## Modules Completed with Estimated %

| Module | % | Status |
|--------|---|--------|
| devices | 75 | FUNCTIONAL |
| notifications | 85 | FUNCTIONAL |
| connections | 70 | FUNCTIONAL |
| home_audio | 65 | FUNCTIONAL |
| mix | 75 | FUNCTIONAL |
| global_search | 70 | FUNCTIONAL |
| radio | 80 | FUNCTIONAL |
| audio_lab | 40 | PARTIAL |
| history | 85 | FUNCTIONAL |
| playlists | 85 | FUNCTIONAL |
| library | 80 | FUNCTIONAL |
| albums | 75 | FUNCTIONAL |
| artists | 70 | FUNCTIONAL |
| folders | 50 | PARTIAL |
| sources | 80 | FUNCTIONAL |
| command_palette | 60 | FUNCTIONAL |
| michi_ai | 65 | FUNCTIONAL |
| metadata | 75 | FUNCTIONAL |
| tagging | 75 | FUNCTIONAL |
| library_doctor | 65 | FUNCTIONAL |
| eq | 80 | FUNCTIONAL |
| outputs | 80 | FUNCTIONAL |
| settings | 15 | SHELL_ONLY |
| home | 60 | FUNCTIONAL |
| lyrics | 80 | FUNCTIONAL |
| disc_lab | 35 | PARTIAL |
| nowplaying | 85 | FUNCTIONAL |
| queue | 80 | FUNCTIONAL |

## Key Improvements per Module

### devices
- DevicesBridge with sync_manager, device_sync_service wiring
- DevicePairingPage, DeviceTransferPanel, DeviceStoragePanel QML components
- Transfer job lifecycle: create, execute, cancel, retry, history
- QR code pairing, browse files on device

### notifications
- NotificationBridge with queue, persistent, progress, action execution
- NotificationCenter, NotificationToast, NotificationBanner QML components
- Action registry integration for undo/retry/navigate

### connections
- ConnectionsBridge with MichiLink controller wiring
- Server discovery, manual connection, pairing, diagnostics
- Retry with backoff, contract verification

### home_audio
- HomeAudioBridge with HA controller + Snapcast controller wiring
- ZoneCard, ZoneDetailPage, GroupEditorPage QML pages
- Latency control, diagnostics, playback transfer

### mix
- MixBridge with query_service, worker_manager wiring
- MixGeneratorPage, MixResultPage, MixExplanationDrawer QML pages
- 12 mix categories, save as playlist, explanation support

### global_search
- GlobalSearchBridge with search service wiring
- GlobalSearchOverlay, SearchFiltersDrawer, SearchResultSection QML components
- Sectioned results (track, album, artist, playlist, folder)

### radio
- RadioBridge with radio_manager, player_service wiring
- RadioStationDetailPage, RadioEditorDialog, RadioImportDialog QML pages
- Favorites, history, search, play/stop

### audio_lab
- AudioLabBridge with AudioLabService + AudioLabState wiring
- 9 sub-pages: Overview, Analysis, Conversion, Normalization, ReplayGain, Integrity, Comparison, Jobs, Profiles
- Job management bridge integration

### history
- HistoryBridge with HistoryListModel, query_service wiring
- HistoryTable, HistoryTimeline, HistoryExportDialog, HistoryStatisticsPage QML pages
- Retention control, filter bar, play from history

### playlists
- PlaylistsBridge with playlist_service, player_service wiring
- PlaylistDetailPage, PlaylistEditorDialog, PlaylistExportDialog, PlaylistImportDialog QML pages
- SmartPlaylistEditorPage, batch delete, M3U import/export

### library
- LibraryBridge with 9-state state machine, query_service wiring
- LibraryPage with tabs (Songs/Albums/Artists/Folders), TrackTable, AlbumGrid
- AlbumDetailPage, ArtistDetailPage, FolderBrowserPage
- Format/genre/year filtering, sort, pagination

### albums/artists/folders
- AlbumGridView, AlbumListView, AlbumCoverFlowView, AlbumMagazineView, AlbumTimelineView, AlbumVinylWallView
- ArtistGridPage, ArtistDetailPage with shuffle
- FolderBrowserPage with breadcrumb, tree view, context menu

### sources
- LibrarySourcesBridge with LibrarySourcesService wiring
- SourcesPage with add/edit/remove/scan/toggle/priority
- SourceExclusionEditor, SourceScanProgress

### command_palette
- CommandPaletteBridge with ActionRegistry wiring
- Search/filter/navigate/execute workflow
- Keyboard handling (Escape/Return)

### michi_ai
- MichiAIBridge with ai_controller, context_service, plan_builder wiring
- AssistantPage with ChatBubble, SuggestionCard
- 8 states (idle→understanding→planning→awaiting_confirmation→executing→completed→cancelled→failed)
- Destructive action confirmation, tool registry

### metadata
- MetadataBridge with metadata_service wiring
- MetadataPage, MetadataFieldGrid, MetadataDiffView, MetadataWriteProgress, MetadataConflictView
- Batch edit, artwork replace/remove

### tagging
- SmartTaggingBridge with metadata_tag_adapter wiring
- SmartTaggingPage with progress, confidence display, status badges
- Preview/select/accept/reject/apply workflow

### library_doctor
- LibraryDoctorBridge with LibraryDoctorScanRepository wiring
- DoctorDryRunPage, DoctorIssueList, DoctorRepairProgress, DoctorReportPage
- 8 issue types (missing_file, duplicate_uid, duplicate_path, etc.)

### eq
- EqBridge with player_service wiring
- EqPage with EqualizerGraph, EqualizerBandControl, EqualizerPresetBrowser
- Graphic 10-band + parametric 6-band modes, bypass, preamp

### outputs
- OutputProfilesBridge with player_service wiring
- OutputProfilesPage with OutputProfileCard, OutputProfileEditor
- Create/duplicate/delete/edit profiles

### settings
- SettingsBridge base implementation
- 7 settings pages: General, Appearance, Playback, Library, Accessibility, Audio, About
- Placeholder status — real settings integration pending

### home
- HomeBridge with db, player_service, library_bridge wiring
- HomePage with library stats, playback status, ecosystem info
- Continue card, add music card, file picker

## New QML Pages Count: 34

## New QML Components Count: 20

| Component | File |
|-----------|------|
| AsyncStateView | ui_qml/components/AsyncStateView.qml |
| CancellationState | ui_qml/components/CancellationState.qml |
| CapabilityGuard | ui_qml/components/CapabilityGuard.qml |
| ConfirmationDialog | ui_qml/components/ConfirmationDialog.qml |
| DegradedState | ui_qml/components/DegradedState.qml |
| DestructiveActionDialog | ui_qml/components/DestructiveActionDialog.qml |
| ErrorState | ui_qml/components/ErrorState.qml |
| InlineValidation | ui_qml/components/InlineValidation.qml |
| JobProgressCard | ui_qml/components/JobProgressCard.qml |
| LoadingState | ui_qml/components/LoadingState.qml |
| NotificationBanner | ui_qml/components/NotificationBanner.qml |
| NotificationCenter | ui_qml/components/NotificationCenter.qml |
| NotificationItem | ui_qml/components/NotificationItem.qml |
| NotificationProgressItem | ui_qml/components/NotificationProgressItem.qml |
| NotificationToast | ui_qml/components/NotificationToast.qml |
| ProgressState | ui_qml/components/ProgressState.qml |
| ResponsivePageLayout | ui_qml/components/ResponsivePageLayout.qml |
| ResponsiveToolbar | ui_qml/components/ResponsiveToolbar.qml |
| SelectionActionBar | ui_qml/components/SelectionActionBar.qml |
| UnavailableState | ui_qml/components/UnavailableState.qml |

## New Test Files Count: 86

Includes workflow tests (14), domain-specific tests (72+ across devices, connections, home_audio, library, mix, notifications, playlists, radio, search, history, metadata, tagging, eq, outputs, ai, command_palette, home, accessibility, settings).

## Context Bindings Required: 44

See `ui_qml_bridge/context_bindings.py` for the complete mapping of QML context property names to bridge keys.

## Routes Required: 61

See `ui_qml_bridge/route_registry.py` for the complete route table across categories: core (12), library (10), detail (14), tools (20), settings (8), system (2).

## Dependencies Pending

- audio_lab: waveform rendering, batch jobs start/cancel, analysis/conversion/normalization/replaygain/integrity/comparison execution
- folders: folder health diagnostics, integrity checks
- settings: all 7 setting pages need real SettingsBridge integration
- home: homeBridge integration (currently no bridge calls in HomePage)
- mix: MixRuleEditor bridge integration
- library_doctor: scan/fix execution, real report generation
- tagging: batch workflow (multiple files)
- disc_lab: rip functionality, CDDB/MusicBrainz lookup
- metadata: artwork extraction from tags

## Known Failures

- audio_lab: analysis/conversion/normalization/replaygain/integrity/comparison sub-pages are UI-only, not connected to bridge
- settings: all setting pages except sources are PlaceholderPage
- home: library stats (albums/artists/tracks) may show 0 without homeBridge integration
- library_doctor: scan and fix buttons exist but bridge calls are placeholders
- discs_lab: rip button disabled, no CDDB/MusicBrainz lookup
- folders: health diagnostics and integrity checks not wired

## Pendientes post-commit

### Service construction issues (ad-hoc instantiation bypassing DI)

| Bridge | File | Issue |
|--------|------|-------|
| AudioLabBridge | `audio_lab_bridge.py:380` | `AudioProbeService()` created ad-hoc in `probeFile()` fallback |
| AudioLabBridge | `audio_lab_bridge.py:393` | `AudioAnalysisService()` created ad-hoc in `analyzeFile()` fallback |
| AudioLabBridge | `audio_lab_bridge.py:408` | `AudioIntegrityService()` created ad-hoc in `integrityCheck()` fallback |
| AudioLabBridge | `audio_lab_bridge.py:422` | `AudioComparisonService()` created ad-hoc in `compareFiles()` fallback |
| LibraryBridge | `library_bridge.py:717` | `LibrarySourcesService(db=self._db)` created ad-hoc in `addFolder()` |
| LibrarySourcesBridge | `library_sources_bridge.py:19` | `LibrarySourcesService()` fallback in `__init__` |
| JobBridge | `job_bridge.py:155` | `LibrarySourcesService(db=self._db)` created ad-hoc in `_scan_all_sources()` |

All of these should be migrated to constructor injection via `AppContext`/`AppServices`.

## Expected Conflicts with Main Front

1. **route_registry.py** — added new routes (devices.detail, devices.pairing, connections.detail, zone_detail, group_editor, mix_generator, mix_result, settings.*, library_doctor, tagging, equalizer, outputs, and many more)
2. **context_bindings.py** — 44 context properties (this file may not exist in main front; if it does, merge additions)
3. **ui_qml/pages/** — 34 new page QML files + 59 modified existing pages
4. **ui_qml/components/** — 20 new component QML files
5. **tests/qml/** — 86 new test files + 26 modified
6. **devices_bridge.py** — modified with new methods (browseFiles, ejectDevice, clearTransferHistory)

## Merge/Cherry-pick Instructions

### Strategy: Feature branch merge into main front

```bash
# 1. Ensure main front is up to date
git checkout main
git pull origin main

# 2. Merge the domain parity branch
git merge qml-domain-parity

# 3. Resolve expected conflicts:
#    - ui_qml_bridge/route_registry.py: accept both sets of routes, deduplicate
#    - ui_qml_bridge/context_bindings.py: accept new file if not present
#    - devices_bridge.py: accept our version (adds browseFiles, ejectDevice, clearTransferHistory)

# 4. Verify
ruff check . --output-format concise
python -m compileall -q -x '.venv/|\.tmpl\.' .
python -m pytest tests/qml/ -q
```

### If cherry-pick is preferred:

```bash
# Cherry-pick commits in chronological order.
# Key commits to pick:
# - route_registry updates
# - devices_bridge changes
# - All new QML pages and test files
# - Bridge files and their tests

# After cherry-pick, verify context_bindings.py has all 44 entries.
```
