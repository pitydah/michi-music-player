# FROZEN APIs — Michi QML Functional Wave

> Do not modify without updating all callers and tests.
> Last freeze: 2026-07-14

---

## 1. Bridge Constructors

| Bridge | Constructor Signature | File |
|---|---|---|
| DevicesBridge | `(sync_manager=None, device_sync_service=None, job_service=None, parent=None)` | `ui_qml_bridge/devices_bridge.py:60` |
| AudioLabBridge | `(audio_lab_service=None, job_service=None, confirmation_service=None, db_conn=None, navigation_bridge=None, player_service=None, worker_manager=None, parent=None)` | `ui_qml_bridge/audio_lab_bridge.py:18` |
| MixBridge | `(db=None, player_service=None, track_action_service=None, playlist_bridge=None, query_executor=None, worker_manager=None, parent=None)` | `ui_qml_bridge/mix_bridge.py` |
| ConnectionsBridge | `(michi_link_controller=None, navigation_bridge=None, settings_manager=None, parent=None)` | `ui_qml_bridge/connections_bridge.py` |
| HomeAudioBridge | `(ha_controller=None, snapcast_ctrl=None, parent=None)` | `ui_qml_bridge/home_audio_bridge.py:24` |
| NotificationBridge | `(action_registry=None, job_bridge=None, notification_service=None, navigation_bridge=None, diagnostics_service=None, parent=None)` | `ui_qml_bridge/notification_bridge.py:21` |
| RadioBridge | `(radio_manager=None, player_service=None, parent=None)` | `ui_qml_bridge/radio_bridge.py:10` |
| GlobalSearchBridge | `(search_service=None, parent=None)` | `ui_qml_bridge/global_search_bridge.py:30` |
| CapabilityBridge | `(factory=None, parent=None)` | `ui_qml_bridge/capability_bridge.py` |

---

## 2. Context Names (Property Names)

| Bridge | Property | Type |
|---|---|---|
| DevicesBridge | `serverActive` | bool |
| DevicesBridge | `serverPort` | int |
| DevicesBridge | `peers` | QVariantList |
| DevicesBridge | `pairedDevices` | QVariantList |
| DevicesBridge | `discovered` | QVariantList |
| DevicesBridge | `transferJobs` | QVariantList |
| DevicesBridge | `transferHistory` | QVariantList |
| DevicesBridge | `storageInfo` | QVariantList |
| DevicesBridge | `compatibilityInfo` | QVariantList |
| AudioLabBridge | `modules` | QVariantList |
| AudioLabBridge | `totalTracks` | int |
| AudioLabBridge | `missingMetadata` | int |
| AudioLabBridge | `missingCovers` | int |
| AudioLabBridge | `backendInfo` | dict |
| AudioLabBridge | `pipelineInfo` | dict |
| AudioLabBridge | `dspInfo` | dict |
| MixBridge | `categories` | QVariantList |
| MixBridge | `currentSongs` | QVariantList |
| MixBridge | `currentMixTitle` | str |
| MixBridge | `errorMessage` | str |
| MixBridge | `currentMixId` | str |
| ConnectionsBridge | `microServerState` | str |
| ConnectionsBridge | `microServerAlias` | str |
| ConnectionsBridge | `microServerContract` | str |
| ConnectionsBridge | `lastError` | str |
| ConnectionsBridge | `latencyMs` | int |
| ConnectionsBridge | `serverVersion` | str |
| ConnectionsBridge | `discoveredServers` | QVariantList |
| ConnectionsBridge | `capabilities` | QVariantList |
| ConnectionsBridge | `lastContact` | float |
| ConnectionsBridge | `externalServers` | QVariantList |
| ConnectionsBridge | `protocol` | str |
| ConnectionsBridge | `compatible` | bool |
| HomeAudioBridge | `homeAssistantState` | str |
| HomeAudioBridge | `snapcastState` | str |
| HomeAudioBridge | `devices` | QVariantList |
| HomeAudioBridge | `zones` | QVariantList |
| HomeAudioBridge | `groups` | QVariantList |
| HomeAudioBridge | `receivers` | QVariantList |
| HomeAudioBridge | `lastError` | str |
| HomeAudioBridge | `lastContact` | float |
| HomeAudioBridge | `sourceInfo` | dict |
| HomeAudioBridge | `syncStatus` | dict |
| HomeAudioBridge | `homeAssistantAvailable` | bool |
| HomeAudioBridge | `snapcastAvailable` | bool |
| HomeAudioBridge | `receiversAvailable` | bool |
| HomeAudioBridge | `zonesSupported` | bool |
| HomeAudioBridge | `groupingSupported` | bool |
| HomeAudioBridge | `volumeSupported` | bool |
| NotificationBridge | `currentNotification` | QVariant |
| NotificationBridge | `queueLength` | int |
| NotificationBridge | `persistentNotifications` | QVariantList |
| RadioBridge | `stations` | QVariantList |
| RadioBridge | `favorites` | QVariantList |
| RadioBridge | `history` | QVariantList |
| GlobalSearchBridge | `query` | str |
| GlobalSearchBridge | `results` | QVariantList |
| GlobalSearchBridge | `isSearching` | bool |
| GlobalSearchBridge | `errorCode` | str |
| GlobalSearchBridge | `errorMessage` | str |
| CapabilityBridge | `capabilities` | QVariantMap |

---

## 3. Route IDs

| Route | Target Page |
|---|---|
| `devices.list` | DevicesPage |
| `devices.detail(device_id)` | DeviceDetailPage |
| `devices.pairing` | DevicePairingPage |
| `audio_lab.overview` | AudioLabOverviewPage |
| `audio_lab.analysis` | AudioAnalysisPage |
| `audio_lab.conversion` | AudioConversionPage |
| `audio_lab.normalization` | AudioNormalizationPage |
| `audio_lab.replaygain` | ReplayGainPage |
| `audio_lab.integrity` | AudioIntegrityPage |
| `audio_lab.comparison` | AudioComparisonPage |
| `audio_lab.jobs` | AudioBatchJobsPage |
| `audio_lab.profiles` | AudioConversionProfileEditor |
| `mix` | MixHubPage |
| `mix_detail(mix_id)` | MixDetailPage |
| `mix_generator` | MixGeneratorPage |
| `mix_result` | MixResultPage |
| `mix_rule_editor` | MixRuleEditorPage |
| `connections` | ConnectionsPage |
| `connections.detail(connection_id)` | ConnectionDetailPage |
| `home_audio` | HomeAudioPage |
| `radio` | RadioPage |
| `search` | GlobalSearchPage |

All routes are registered in `NavigationBridge.VALID_ROUTES`.

---

## 4. objectNames

### DevicesPage
| objectName | Control |
|---|---|
| `devices.devicesPage` | Main page Item |
| `devices.syncStatusPanel` | SyncStatusPanel |
| `devices.pairedDevicesHeader` | SectionHeader "Dispositivos emparejados" |
| `devices.pairedDeviceCard_{index}` | DeviceCard (paired) |
| `devices.networkPeersHeader` | SectionHeader "Pares detectados en red" |
| `devices.networkPeerCard_{index}` | DeviceCard (network) |
| `devices.devicePairingDialog` | DevicePairingDialog |
| `devices.deviceStorageView` | DeviceStorageView |
| `devices.deviceTransferQueue` | DeviceTransferQueue |

### AudioLabOverviewPage
| objectName | Control |
|---|---|
| `audioLab.audioLabOverviewPage` | Main page Item |
| `audioLab.hero` | HeroMaterial |
| `audioLab.toolsHeader` | SectionHeader "Herramientas" |
| `audioLab.statusBadge` | StatusBadge |
| `audioLab.cardAnalysis` | GlassCard "Análisis técnico" |
| `audioLab.cardConversion` | GlassCard "Conversión" |
| `audioLab.cardNormalization` | GlassCard "Normalización" |
| `audioLab.cardReplayGain` | GlassCard "ReplayGain" |
| `audioLab.cardIntegrity` | GlassCard "Integridad" |
| `audioLab.cardComparison` | GlassCard "Comparación" |
| `audioLab.cardJobs` | GlassCard "Trabajos" |
| `audioLab.cardProfiles` | GlassCard "Perfiles" |
| `audioLab.backendHeader` | SectionHeader "Estado del backend" |
| `audioLab.backendInfoPanel` | Backend info panel |
| `audioLab.statusInfo` | Status info glass |
| `audioLab.experimentalBadge` | StatusBadge "Experimental" |
| `audioLab.ffmpegBadge` | StatusBadge "Requiere ffmpeg" |
| `audioLab.bridgeStatus` | StatusBadge bridge unavailable |
| `audioLab.selectionSummary` | AudioSelectionSummary |

### MixHubPage
| objectName | Control |
|---|---|
| `mix.mixHubPage` | Main page Item |
| `mix.hero` | HeroMaterial |
| `mix.yourMixesHeader` | SectionHeader "Tus mixes" |
| `mix.mixCard_{index}` | GlassCard |
| `mix.smartMixesHeader` | SectionHeader "Smart Mixes" |
| `mix.mixByArtistButton` | MichiButton "+ Mix por artista" |
| `mix.mixByGenreButton` | MichiButton "+ Mix por género" |
| `mix.mixByDecadeButton` | MichiButton "+ Mix por década" |
| `mix.mixAdvancedRulesButton` | MichiButton "Reglas avanzadas" |
| `mix.bridgeStatus` | StatusBadge bridge unavailable |

### ConnectionsPage
| objectName | Control |
|---|---|
| `connections.connectionsPage` | Main page Item |
| `connections.microServerHero` | MicroServerHero |
| `connections.externalServersHeader` | SectionHeader "Servidores externos" |
| `connections.externalServerCard_{index}` | ExternalServerCard |
| `connections.networkDiscoveryPanel` | NetworkDiscoveryPanel |
| `connections.homeAudioAccess` | HomeAudioAccess |

### HomeAudioPage
| objectName | Control |
|---|---|
| `homeAudio.homeAudioPage` | Main page Item |
| `homeAudio.modeSelector` | HomeAudioModeSelector |
| `homeAudio.haPanel` | HomeAssistantPanel |
| `homeAudio.streamPanel` | MichiMusicStreamPanel |
| `homeAudio.zoneHeaderRow` | Row header row |
| `homeAudio.zonesHeader` | SectionHeader "Zonas" |
| `homeAudio.createGroupButton` | MichiButton "Crear grupo" |
| `homeAudio.zoneCardItem_{index}` | ZoneCard wrapper |
| `homeAudio.zoneCard_{index}` | ZoneCard |
| `homeAudio.devicesHeader` | SectionHeader "Dispositivos" |
| `homeAudio.receiverCard_{index}` | ReceiverCard |
| `homeAudio.networkDiagnosticsCard` | GlassCard diagnóstico |
| `homeAudio.experimentalBadge` | StatusBadge "Experimental" |

### RadioPage
| objectName | Control |
|---|---|
| `radio.radioPage` | Main page Item |
| `radio.hero` | HeroMaterial |
| `radio.searchField` | SearchField |
| `radio.favoritesSection` | SectionHeader "Favoritas" |
| `radio.favoriteStation_{index}` | RadioStationDetail |
| `radio.allStationsHeader` | SectionHeader "Todas las emisoras" |
| `radio.allStation_{index}` | RadioStationDetail |
| `radio.addStationButton` | MichiButton "Añadir emisora" |
| `radio.newStationName` | SearchField nombre |
| `radio.newStationUrl` | SearchField URL |
| `radio.newStationCodec` | SearchField codec |
| `radio.newStationCountry` | SearchField país |
| `radio.confirmAddStation` | MichiButton confirmar |
| `radio.historySection` | SectionHeader "Historial" |
| `radio.statusBadge` | StatusBadge |

### GlobalSearchPage
| objectName | Control |
|---|---|
| `globalSearch.page` | Main page Item |
| `globalSearch.hero` | HeroMaterial |
| `globalSearch.openFiltersBtn` | MichiButton "Filtros" |
| `globalSearch.clearSearchBtn` | MichiButton "Limpiar" |
| `globalSearch.input` | SearchField |
| `globalSearch.searchResultSection_{index}` | SearchResultSection |
| `globalSearch.recentColumn` | SearchRecentQueries |
| `globalSearch.suggestionsColumn` | SearchSuggestions |
| `globalSearch.searchingText` | Text "Buscando..." |
| `globalSearch.errorState` | ErrorState |
| `globalSearch.noResultsText` | Text "Sin resultados" |

---

## 5. Model Roles

| Bridge | Model | Roles |
|---|---|---|
| DevicesBridge | `peers` | `alias`, `device`, `ip`, `port` |
| DevicesBridge | `pairedDevices` | `alias`, `device` |
| AudioLabBridge | `modules` | `id`, `title`, `desc`, `status` |
| MixBridge | `categories` | `id`, `title`, `icon`, `desc` |
| ConnectionsBridge | `discoveredServers` | `name`, `ip`, `port`, `protocol`, `version` |
| ConnectionsBridge | `externalServers` | `name`, `serverType`, `apiType` |
| HomeAudioBridge | `zones` | `name`, `devices`, `state`, `status`, `muted`, `volume`, `latency_ms`, `id` |
| HomeAudioBridge | `devices` | `name`, `room`, `state`, `type` |
| HomeAudioBridge | `groups` | `id`, `name`, `zones` |
| RadioBridge | `stations` | `id`, `name`, `url`, `codec`, `country`, `tags`, `favorite` |
| RadioBridge | `favorites` | `id`, `name`, `url`, `codec`, `country`, `tags`, `favorite` |
| RadioBridge | `history` | `name`, `url`, `played_at` |
| GlobalSearchBridge | `results` | `section`, `title`, `id`, `subtitle` |

---

## 6. Error Codes

| Domain | Error Code |
|---|---|
| Devices | `NO_SYNC_MANAGER` |
| Devices | `NO_DEVICE_SYNC_SERVICE` |
| Devices | `DEVICE_NOT_FOUND` |
| Devices | `VIDEO_NOT_SUPPORTED` |
| Devices | `UNSUPPORTED_FORMAT` |
| Devices | `JOB_NOT_FOUND` |
| Devices | `JOB_NO_SOURCE` |
| Devices | `NO_DEVICE_KEY` |
| Devices | `NO_MOUNT_POINT` |
| Devices | `EJECT_NOT_SUPPORTED` |
| Devices | `JOB_ALREADY_COMPLETED` |
| Devices | `INSUFFICIENT_STORAGE` |
| Audio Lab | `UNSUPPORTED` |
| Mix | `EMPTY_MIX` |
| Mix | `NO_TRACK_ID` |
| Mix | `PLAY_FAILED` |
| Mix | `NO_PLAYBACK` |
| Mix | `ENQUEUE_FAILED` |
| Mix | `INVALID_INDEX` |
| Mix | `SAVE_FAILED` |
| Mix | `CREATE_FAILED` |
| Mix | `EMPTY_NAME` |
| Mix | `NO_PLAYLIST_BRIDGE` |
| Connections | State machine: `not_configured` → `scanning` → `detected` → `pairing_required` → `paired` → `connected` → `error` |
| Connections | `PAIRING_FAILED` |
| Home Audio | `UNSUPPORTED` |
| Home Audio | `NOT_IMPLEMENTED` |
| Home Audio | `CONNECTION_FAILED` |
| Home Audio | `EMPTY_ZONE` |
| Home Audio | `EMPTY_ZONES` |
| Home Audio | `MISSING_ARGS` |
| Home Audio | `EMPTY_SOURCE` |
| Notifications | `NO_CURRENT_NOTIFICATION` |
| Notifications | `NO_ACTION` |
| Notifications | `NOT_FOUND` |
| Notifications | `INVALID_TRACK` |
| Notifications | `NO_ACTION_REGISTRY` |
| Notifications | `NO_NAVIGATION_TARGET` |
| Notifications | `UNSUPPORTED` |
| Notifications | `NO_NAVIGATION` |
| Radio | `EMPTY_URL` |
| Radio | `NO_RADIO_MANAGER` |
| Radio | `NO_PLAYER_SERVICE` |
| Radio | `NO_PLAYER` |
| Radio | `NO_LAST_STATION` |
| Radio | `NO_STATIONS` |
| Radio | `FILE_NOT_FOUND` |
| Radio | `NO_METADATA` |
| Radio | `NOT_IMPLEMENTED` |
| Global Search | `SERVICE_UNAVAILABLE` |
| Global Search | `SEARCH_FAILED` |
| Global Search | `UNKNOWN_DOMAIN` |
| Global Search | `NO_BRIDGE` |

---

## 7. Job Interactions

| Bridge | Method | Purpose |
|---|---|---|
| DevicesBridge | `startTransfer(source, dest)` | Start file transfer |
| DevicesBridge | `cancelTransfer(job_id)` | Cancel active transfer |
| DevicesBridge | `retryTransfer(job_id)` | Retry failed transfer |
| DevicesBridge | `clearTransferHistory()` | Clear transfer log |
| MixBridge | `cancelGeneration()` | Cancel active mix generation |
| ConnectionsBridge | `_cancel_op()` | Cancel async operation |
| HomeAudioBridge | `_cancel_retry()` | Cancel retry loop |
| NotificationBridge | `dismiss()` | Dismiss current notification |
| NotificationBridge | `clear()` | Clear all notifications |
| RadioBridge | `stopStream()` | Stop radio stream playback |
| GlobalSearchBridge | `cancel()` | Cancel active search |

---

## 8. Capability State Values

| Capability | Default State | Services Required |
|---|---|---|
| `library` | available | `db` |
| `playback` | available | `player_service` |
| `nowplaying` | available | `player_service` |
| `mix` | available | `db` |
| `lyrics` | available | `worker_manager` |
| `connections_michilink` | available | `michi_link_controller` |
| `home_audio` | deferred_physical | `home_audio_controller` (DEFERRED_PHYSICAL if only `snapcast_controller`) |
| `snapcast` | available | `snapcast_controller` |
| `devices_sync` | available | `sync_manager` |
| `radio` | available | `radio_manager` |
| `playlists` | available | `db` |
| `eq` | available | `player_service` |
| `settings` | available | none |
| `audio_lab` | available | none |
| `metadata` | available | none |
| `smart_tagging` | available | `smart_tagging_service` |
| `disc_lab` | deferred_physical | `disc_service` (DEFERRED_PHYSICAL if only `db`) |
| `library_doctor` | available | `db` |
| `diagnostics` | available | `db` |
| `michi_ai` | available | none |
| `theme` | available | none |
| `navigation` | available | none |
| `route_registry` | available | none |
| `app_state` | available | none |
| `command_palette` | available | none |
| `cover` | available | none |
| `notifications` | available | none |
| `global_search` | available | `search_service` |

---

## 9. Breakpoints (Responsive)

| Label | Width |
|---|---|
| Wide | > 1400px |
| Standard | 1024-1400px |
| Compact | 768-1023px |
| Narrow | < 768px |
| 125% scaling | width × 1.25 |
| 150% scaling | width × 1.5 |

---

## 10. Accessibility Baseline

| Requirement | Implementation |
|---|---|
| Keyboard navigation | `activeFocusOnTab: true`, `KeyNavigation.tab`/`backtab` |
| Keyboard activation | `Keys.onReturnPressed`, `Keys.onSpacePressed` |
| Focus management | `focus: true` on root Item |
| Accessible roles | `Accessible.role: Accessible.Pane`, `Grouping`, `Button`, `AlertMessage` |
| Accessible names | `Accessible.name` on all interactive elements |
| Progress announcements | `Accessible.description` with checking state |
| Error announcements | `Accessible.description` with error code |
| Dialog focus trap | `KeyNavigation.tab` circular within dialogs |
| Font scaling | `MichiTheme.typography` pixel sizes throughout |
| Reduced motion | `MichiTheme.motion` respected |

---

## Modification Protocol

To modify any frozen API:

1. Update all tests that reference the changed API
2. Update all QML pages that consume the changed API
3. Update this document
4. Run `ruff check .` — must be 0
5. Run `python -m pytest tests/qml/ -q` — must pass
6. Update version marker in `FROZEN_APIS.md`
