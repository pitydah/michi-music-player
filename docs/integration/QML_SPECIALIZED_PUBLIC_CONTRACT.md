# QML Specialized Public Contract — Domain Inventory

> Macrofase MA — one entry per specialized domain.

---

## 1. Devices

| Field | Value |
|---|---|
| **Routes** | `devices.list`, `devices.detail(device_id)`, `devices.pairing` |
| **Pages** | `pages/devices/DevicesPage.qml`, `DeviceDetailPage`, `DevicePairingPage`, `DeviceCard`, `DeviceStoragePanel`, `DeviceStorageView`, `DeviceSyncHistory`, `DeviceSyncProfileEditor`, `DeviceTransferJob`, `DeviceTransferQueue`, `DeviceTransferPanel`, `DeviceCompatibilityView`, `SyncStatusPanel`, `DevicePairingDialog` |
| **Bridge** | `devices_bridge.py` (`DevicesBridge`, QObject, 488 lines) |
| **Models** | `peers`, `pairedDevices`, `discovered`, `transferJobs`, `transferHistory`, `storageInfo`, `compatibilityInfo` (all `QVariantList`) |
| **Primary action** | Sync audio files between Michi instances / portable devices |
| **Jobs** | `startTransfer(source, dest)`, `cancelTransfer(job_id)`, `retryTransfer(job_id)`, `clearTransferHistory()` |
| **Cancellation** | `cancelTransfer(job_id)` → `_dev_svc.cancel_job(job_id)` |
| **Errors** | `NO_SYNC_MANAGER`, `NO_DEVICE_SYNC_SERVICE`, `DEVICE_NOT_FOUND`, `VIDEO_NOT_SUPPORTED`, `UNSUPPORTED_FORMAT`, `JOB_NOT_FOUND`, `JOB_NO_SOURCE`, `NO_DEVICE_KEY`, `NO_MOUNT_POINT`, `EJECT_NOT_SUPPORTED`, `JOB_ALREADY_COMPLETED`, `INSUFFICIENT_STORAGE` |
| **Capabilities** | `devices_sync` requires `sync_manager`; states: AVAILABLE, UNAVAILABLE, DEFERRED_PHYSICAL |
| **Physical dependency** | `sync.SyncManager` (UDP multicast discovery + REST API); `DeviceSyncService` for portable devices |
| **Legacy equivalent** | `ui/devices_page.py` (QtWidgets Sync page) |
| **Remaining gaps** | No video support (intentional); MTP protocol pairing untested in QML; transfer progress bars depend on service events |

---

## 2. Audio Lab

| Field | Value |
|---|---|
| **Routes** | `audio_lab.overview`, `audio_lab.analysis`, `audio_lab.conversion`, `audio_lab.normalization`, `audio_lab.replaygain`, `audio_lab.integrity`, `audio_lab.comparison`, `audio_lab.jobs`, `audio_lab.profiles`, `audio_lab_job_detail(job)` |
| **Pages** | `AudioLabOverviewPage`, `AudioAnalysisPage`, `AudioConversionPage`, `AudioNormalizationPage`, `ReplayGainPage`, `AudioIntegrityPage`, `AudioComparisonPage`, `AudioBatchJobsPage`, `AudioConversionProfileEditor`, `AudioJobDetail`, `AudioLabResultsPage`, `AudioInputSelection`, `AudioSelectionSummary`, `AudioTechnicalReport`, `AudioWaveformSummary`, `ComparisonPanel` |
| **Bridge** | `audio_lab_bridge.py` (`AudioLabBridge`, QObject, 237 lines) |
| **Models** | `modules` (QVariantList), `totalTracks`, `missingMetadata`, `missingCovers`, `backendInfo`, `pipelineInfo`, `dspInfo` |
| **Primary action** | Diagnostics, health, conversion, integrity, comparison, analysis of audio files |
| **Jobs** | Delegated to `AudioIntegrityService`, `AudioProbeService`, `AudioAnalysisService` |
| **Cancellation** | Cancellation via job service; modules map via `navigateTo(module_id)` |
| **Errors** | `UNSUPPORTED` if no navigation backend; per-service exceptions caught and returned as `{"ok": False, "error": ...}` |
| **Capabilities** | `audio_lab` always AVAILABLE; modules graded `available` or `experimental` based on backend presence |
| **Physical dependency** | `player_service` (for backend/eq info), `db_conn` (for library health), `navigation_bridge` |
| **Legacy equivalent** | `ui/audio_lab/` (QtWidgets diagnostics pages, `AudioLabDiagnosticsPage`) |
| **Remaining gaps** | Conversion and Vinyl modules marked `experimental`; periodic analyzer not implemented |

---

## 3. Mix

| Field | Value |
|---|---|
| **Routes** | `mix`, `mix_detail(mix_id)`, `mix_generator`, `mix_result`, `mix_rule_editor` |
| **Pages** | `MixHubPage`, `MixDetailPage`, `MixGeneratorPage`, `MixResultPage`, `MixRuleEditorPage`, `MixRuleEditor`, `MixGenerationProgress`, `MixFeedbackControls`, `MixExplanationDrawer`, `MixExplanationPanel` |
| **Bridge** | `mix_bridge.py` (`MixBridge`, QObject, 337 lines) |
| **Models** | `categories`, `currentSongs`, `currentMixTitle`, `errorMessage`, `currentMixId` |
| **Primary action** | Load curated/recommended song lists (mix categories) and play/enqueue/save |
| **Jobs** | `cancelGeneration()` signals worker manager; generation progress via `generationProgress` signal |
| **Cancellation** | `cancelGeneration()` → `_wm.cancel_all(owner="mix_bridge")` + generation counter bump |
| **Errors** | `EMPTY_MIX`, `NO_TRACK_ID`, `PLAY_FAILED`, `NO_PLAYBACK`, `ENQUEUE_FAILED`, `INVALID_INDEX`, `SAVE_FAILED`, `CREATE_FAILED`, `EMPTY_NAME`, `NO_PLAYLIST_BRIDGE` |
| **Capabilities** | `mix` requires `db`; states: AVAILABLE, UNAVAILABLE; category list excludes `ai_recommended` when AI disabled |
| **Physical dependency** | `db`, `playback_ctrl` or `player_service`, `track_action_service`, `playlist_bridge`, `query_executor`, `worker_manager` |
| **Legacy equivalent** | `core/recommendation/` engine + `ui/controllers/smart_playlist_controller.py` |
| **Remaining gaps** | AI mixes not implemented; `daily_mix` uses simple recent+unplayed heuristic |

---

## 4. Connections (Michi Link)

| Field | Value |
|---|---|
| **Routes** | `connections`, `connections.detail(connection_id)` |
| **Pages** | `ConnectionsPage`, `ConnectionDetailPage`, `ConnectionCard`, `ConfiguredServerCard`, `DiscoveredServerCard`, `ExternalServerCard`, `ConnectionCapabilities`, `ConnectionErrorPanel`, `ConnectionSetupWizard`, `HomeAudioAccess`, `ManualConnectionDialog`, `MicroServerHero`, `NetworkDiscoveryPanel`, `PairingDialog`, `ServerDiscoveryView` |
| **Bridge** | `connections_bridge.py` (`ConnectionsBridge`, QObject, 375 lines) |
| **Models** | `microServerState`, `microServerAlias`, `microServerContract`, `lastError`, `latencyMs`, `serverVersion`, `discoveredServers`, `capabilities`, `lastContact`, `externalServers`, `protocol`, `compatible` |
| **Primary action** | Discover, pair, connect to Michi Micro Servers on LAN |
| **Jobs** | Async operations via `_AsyncOp` (threading + deadlines); retry with exponential backoff (`_MAX_RETRIES=3`) |
| **Cancellation** | `_cancel_op()` → `_AsyncOp.cancel()` + `QTimer.stop()`; scan returns `CANCELLED` on interrupt |
| **Errors** | State machine: `not_configured` → `scanning` → `detected` → `pairing_required` → `paired` → `connected` → `error`; typed error strings via `_typed_error`; `PAIRING_FAILED` |
| **Capabilities** | `connections_michilink` requires `michi_link_controller`; capabilities: `can_continue_playback`, `can_import`, `can_send_genre_playlist`, `can_send_genre_mix` |
| **Physical dependency** | `michi_link_ctrl` (`MichiLinkController`); `settings_manager` for host/port/alias persistence |
| **Legacy equivalent** | `ui/controllers/michi_link_controller.py` (QtWidgets) |
| **Remaining gaps** | `_DEMO_ENABLED = False`; contract negotiation only after `confirmPair`; no external server support |

---

## 5. Home Audio

| Field | Value |
|---|---|
| **Routes** | `home_audio` |
| **Pages** | `HomeAudioPage`, `ZoneCard`, `AudioZoneCard`, `GroupEditor`, `GroupEditorPage`, `HomeAssistantPanel`, `HomeAudioModeSelector`, `LatencyControl`, `MichiMusicStreamPanel`, `MultiroomStatus`, `PlaybackTransferDialog`, `ReceiverCard`, `StreamRoutingPage`, `ZoneDetailPage` |
| **Bridge** | `home_audio_bridge.py` (`HomeAudioBridge`, QObject, 409 lines) |
| **Models** | `homeAssistantState`, `snapcastState`, `devices`, `zones`, `groups`, `receivers`, `lastError`, `lastContact`, `sourceInfo`, `syncStatus`, `homeAssistantAvailable`, `snapcastAvailable`, `receiversAvailable`, `zonesSupported`, `groupingSupported`, `volumeSupported` |
| **Primary action** | Multi-room audio: Home Assistant integration + Snapcast zone management |
| **Jobs** | No job queue; retry with backoff via `_retry_with_backoff(target_state)` |
| **Cancellation** | `_cancel_retry()` → `QTimer.stop()` + counter reset |
| **Errors** | `UNSUPPORTED`, `NOT_IMPLEMENTED`, `CONNECTION_FAILED`, `EMPTY_ZONE`, `EMPTY_ZONES`, `MISSING_ARGS`, `EMPTY_SOURCE` |
| **Capabilities** | `home_audio` requires `home_audio_controller`; DEFERRED_PHYSICAL if only `snapcast_controller` available; `snapcast` requires `snapcast_controller` |
| **Physical dependency** | `ha_controller` (Home Assistant API), `snapcast_ctrl` (Snapcast TCP API); settings persistence via `settings_manager` |
| **Legacy equivalent** | `integrations/home_assistant/`, `integrations/snapcast/` |
| **Remaining gaps** | Receiver discovery returns `UNSUPPORTED`; `sourceInfo`/`syncStatus` return empty dicts |

---

## 6. Notifications

| Field | Value |
|---|---|
| **Routes** | No dedicated route — overlays all pages |
| **Pages** | No dedicated page — rendered via `NotificationBridge` QML binding |
| **Bridge** | `notification_bridge.py` (`NotificationBridge`, QObject, 400 lines) |
| **Models** | `currentNotification`, `queueLength`, `persistentNotifications` |
| **Primary action** | Show, queue, dismiss, and execute action notifications (info/success/warning/error + progress) |
| **Jobs** | References `JobBridge` for `openJob`/`cancelJobById`/`retryJob` |
| **Cancellation** | `dismiss()` → `_next()` (dequeue); `clear()` → flush all queues and dedup maps |
| **Errors** | `NO_CURRENT_NOTIFICATION`, `NO_ACTION`, `NOT_FOUND`, `INVALID_TRACK`, `NO_ACTION_REGISTRY`, `NO_NAVIGATION_TARGET`, `UNSUPPORTED`, `NO_NAVIGATION` |
| **Capabilities** | Always AVAILABLE if bridge instantiated; scored via `notificationScore()` (max 100) |
| **Physical dependency** | `action_registry`, `job_bridge`, `notification_service`, `navigation_bridge`, `diagnostics_service` |
| **Legacy equivalent** | `ui/controllers/notification_controller.py` (QtWidgets toast system) |
| **Remaining gaps** | No system notification fallback; accessibility only via `QAccessible.queryAccessibleInterface` (minimal) |

---

## 7. Radio

| Field | Value |
|---|---|
| **Routes** | `radio` |
| **Pages** | `RadioPage`, `RadioStationDetailPage`, `RadioStationDetail`, `RadioSearchView`, `RadioImportDialog`, `RadioEditorDialog`, `RadioEditDialog`, `RadioImportExportPanel` |
| **Bridge** | `radio_bridge.py` (`RadioBridge`, QObject, 249 lines) |
| **Models** | `stations`, `favorites`, `history` |
| **Primary action** | Browse, search, play, manage internet radio stations |
| **Jobs** | No job queue; stream direct via `player_service.play_url()` |
| **Cancellation** | `cancelStream()` / `stopStream()` → `player_service.stop()` |
| **Errors** | `EMPTY_URL`, `NO_RADIO_MANAGER`, `NO_PLAYER_SERVICE`, `NO_PLAYER`, `NO_LAST_STATION`, `NO_STATIONS`, `FILE_NOT_FOUND`, `NO_METADATA`, `NOT_IMPLEMENTED` |
| **Capabilities** | `radio` requires `radio_manager`; states: AVAILABLE, UNAVAILABLE |
| **Physical dependency** | `radio_manager` (internet radio DB + metadata), `player_service` (GStreamer forced for streams) |
| **Legacy equivalent** | `streaming/radio_manager.py` + `ui/controllers/radio_controller.py` (QtWidgets) |
| **Remaining gaps** | `getBitrate()` always returns 0; `getCodec()` returns first station's codec only |

---

## 8. Global Search

| Field | Value |
|---|---|
| **Routes** | `search` |
| **Pages** | `GlobalSearchPage`, `GlobalSearchOverlay`, `SearchFiltersDrawer`, `SearchRecentQueries`, `SearchResultGroup`, `SearchResultItem`, `SearchResultRow`, `SearchResultSection`, `SearchSuggestions` |
| **Bridge** | `global_search_bridge.py` (`GlobalSearchBridge`, QObject, 143 lines) |
| **Models** | `query`, `results`, `isSearching`, `errorCode`, `errorMessage` |
| **Primary action** | Unified search across tracks, albums, artists, playlists, folders, genres, devices, servers, actions, settings |
| **Jobs** | No job queue; synchronous search with request-ID-based stale-guard |
| **Cancellation** | `cancel()` → increments generation counter + cancels service search |
| **Errors** | `SERVICE_UNAVAILABLE` when no `search_service`; `SEARCH_FAILED` on exception; `UNKNOWN_DOMAIN` for invalid domains |
| **Capabilities** | Depends on `search_service` availability; states: AVAILABLE, DEGRADED (limited backends), UNAVAILABLE |
| **Physical dependency** | `search_service` (wraps SQLite FTS5 search engine) |
| **Legacy equivalent** | `library/search_engine.py` (FTS5) + `ui/controllers/search_controller.py` |
| **Remaining gaps** | `searchDomain(domain, query)` prefix-maps domain to `domain:query`; `_MAX_TOTAL=50` hard limit; timeout 5000ms |

---

## 9. Capability States

All specialized domains implement the standardized capability state model:

| State | Meaning |
|---|---|
| `AVAILABLE` | All required services present; full functionality |
| `DEGRADED` | Core services present but some features limited or experimental |
| `UNAVAILABLE` | Required services absent; functionality blocked |
| `DEFERRED_PHYSICAL` | Physical hardware dependency deferred; not an error condition |

This replaces the legacy boolean (True/False) model. No silent hiding. No confusing DEFERRED_PHYSICAL with error.

## 10. Accessibility Requirements

All specialized domain pages must implement:
- Keyboard navigation (`activeFocusOnTab`, `KeyNavigation.tab`, `Keys.onReturnPressed`, `Keys.onSpacePressed`)
- Focus management (`focus: true`, dialog focus trap, focus restoration)
- `Accessible.role` and `Accessible.name` on all interactive elements
- Progress/cancel/error announcements via `Accessible.description`
- Font scaling via `MichiTheme.typography` pixel sizes
- Reduced motion support via `MichiTheme.motion`

## 11. objectName Convention

All specialized page controls follow: `domain.page.control`
- Example: `devices.pairedDevicesHeader`, `radio.favoritesSection`, `mix.mixHero`
- Main pages: `devices.devicesPage`, `audioLab.audioLabOverviewPage`, `mix.mixHubPage`

## 12. Frozen API Surface

See `docs/integration/FROZEN_APIS.md` for the complete list of frozen APIs including:
- Bridge constructors and their parameter signatures
- Context property names
- Route IDs
- objectName values
- Model role names
- Error code strings
- Job interaction methods
