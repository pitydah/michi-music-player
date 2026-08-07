# Reporte de Reachabilidad de Servicios en Tiempo de Ejecución

Generado por `tools/audit_runtime_reachability.py` — 93 entradas de manifest, 80 claves registradas.

## Resumen de estados

| Estado | Cantidad |
|--------|----------|
| LEGACY | 2 |
| ORPHAN | 2 |
| PRODUCTIVE | 51 |
| UNTESTED_VERTICAL | 38 |

## Servicios

| Clave | Clase | Estado | Lifecycle | Consumidores | Bridges | AI tools | Tests unit | Tests vertical |
|---|---|---|---|---|---|---|---|---|
| accessibility_service | AccessibilityService | PRODUCTIVE | managed | 0 | 3 | 0 | 3 | 2 |
| action_registry | ActionRegistry | PRODUCTIVE | managed | 3 | 14 | 0 | 11 | 4 |
| action_registry_binder | unknown | UNTESTED_VERTICAL | passive | 0 | 1 | 0 | 0 | 0 |
| album_repository | AlbumRepository | PRODUCTIVE | passive | 1 | 0 | 0 | 3 | 1 |
| artist_repository | ArtistRepository | UNTESTED_VERTICAL | passive | 1 | 0 | 0 | 0 | 0 |
| artwork_service | CoverArtService | PRODUCTIVE | managed | 2 | 2 | 0 | 3 | 2 |
| audio_lab_job_adapter | unknown | LEGACY | passive | 0 | 0 | 0 | 0 | 0 |
| audio_lab_service | AudioLabService | UNTESTED_VERTICAL | managed | 1 | 3 | 10 | 2 | 0 |
| bridge_factory | unknown | UNTESTED_VERTICAL | passive | 0 | 1 | 0 | 0 | 0 |
| cd_ripper_service | CDRipperService | UNTESTED_VERTICAL | managed | 1 | 4 | 0 | 3 | 0 |
| collection_service | CollectionService | UNTESTED_VERTICAL | managed | 1 | 2 | 0 | 1 | 0 |
| command_palette_bridge | unknown | UNTESTED_VERTICAL | passive | 0 | 2 | 0 | 0 | 0 |
| confirmation_service | ConfirmationService | PRODUCTIVE | managed | 0 | 7 | 0 | 2 | 5 |
| connection_factory | LibraryDB | PRODUCTIVE | managed | 0 | 3 | 0 | 12 | 11 |
| connection_service | ConnectionService | UNTESTED_VERTICAL | managed | 1 | 6 | 0 | 1 | 0 |
| context_service | ContextService | PRODUCTIVE | managed | 3 | 2 | 0 | 13 | 3 |
| database | LibraryDB | PRODUCTIVE | managed | 0 | 8 | 0 | 12 | 11 |
| device_registry | DeviceRegistry | PRODUCTIVE | passive | 1 | 0 | 0 | 1 | 2 |
| device_sync_service | DeviceSyncService | UNTESTED_VERTICAL | managed | 1 | 8 | 11 | 1 | 0 |
| diagnostics_service | DiagnosticsService | PRODUCTIVE | managed | 1 | 4 | 1 | 2 | 1 |
| equalizer_service | EqualizerService | PRODUCTIVE | managed | 1 | 0 | 0 | 2 | 3 |
| event_bus | EventBus | PRODUCTIVE | managed | 0 | 0 | 0 | 3 | 4 |
| favorite_service | FavoriteService | PRODUCTIVE | managed | 4 | 2 | 10 | 2 | 2 |
| folder_service | FolderService | UNTESTED_VERTICAL | managed | 1 | 2 | 0 | 1 | 0 |
| folder_tree_model | FolderTreeModel | UNTESTED_VERTICAL | passive | 1 | 2 | 0 | 1 | 0 |
| genre_cleanup_service | GenreCleanupService | PRODUCTIVE | managed | 1 | 0 | 0 | 1 | 1 |
| genres_service | GenresService | UNTESTED_VERTICAL | managed | 1 | 2 | 0 | 1 | 0 |
| global_search_service | GlobalSearchService | PRODUCTIVE | managed | 1 | 6 | 10 | 2 | 4 |
| history_query_service | HistoryQueryService | PRODUCTIVE | managed | 1 | 3 | 0 | 1 | 1 |
| home_audio_service | HomeAudioService | UNTESTED_VERTICAL | managed | 1 | 7 | 0 | 7 | 0 |
| hybrid_audio_manager | unknown | ORPHAN | passive | 0 | 0 | 0 | 0 | 0 |
| job_bridge | unknown | UNTESTED_VERTICAL | passive | 0 | 9 | 0 | 0 | 0 |
| job_manager | unknown | LEGACY | passive | 0 | 0 | 0 | 0 | 0 |
| job_service | JobService | PRODUCTIVE | managed | 1 | 12 | 0 | 2 | 8 |
| knowledge_broker | unknown | ORPHAN | passive | 0 | 0 | 0 | 0 | 0 |
| library_doctor_scan_repository | LibraryDoctorScanRepository | PRODUCTIVE | passive | 2 | 1 | 0 | 0 | 2 |
| library_doctor_service | LibraryDoctorService | PRODUCTIVE | managed | 2 | 1 | 4 | 2 | 2 |
| library_filtered_query_service | LibraryFilteredQueryService | UNTESTED_VERTICAL | passive | 0 | 0 | 0 | 1 | 0 |
| library_mutation_service | LibraryMutationService | PRODUCTIVE | managed | 4 | 1 | 10 | 1 | 6 |
| library_query_service | LibraryFilteredQueryService | UNTESTED_VERTICAL | managed | 9 | 4 | 10 | 1 | 0 |
| library_service | LibraryService | PRODUCTIVE | managed | 1 | 2 | 0 | 2 | 2 |
| library_sources_service | LibrarySourcesService | UNTESTED_VERTICAL | managed | 2 | 5 | 0 | 0 | 0 |
| lyrics_service | LyricsService | PRODUCTIVE | managed | 1 | 3 | 0 | 1 | 5 |
| metadata_editor_service | MetadataEditorService | PRODUCTIVE | managed | 4 | 2 | 1 | 1 | 4 |
| metadata_service | MetadataService | PRODUCTIVE | managed | 3 | 3 | 1 | 2 | 1 |
| michi_ai_service | unknown | UNTESTED_VERTICAL | managed | 1 | 3 | 0 | 0 | 0 |
| michi_link_client | MichiLinkClient | UNTESTED_VERTICAL | passive | 2 | 0 | 0 | 1 | 0 |
| michi_link_continue_service | ContinueOnServerService | PRODUCTIVE | passive | 1 | 0 | 0 | 3 | 4 |
| michi_link_diagnostics_service | LinkDiagnosticsService | PRODUCTIVE | passive | 0 | 0 | 0 | 1 | 1 |
| michi_link_import_service | ImportToServerService | PRODUCTIVE | passive | 1 | 0 | 0 | 3 | 2 |
| michi_link_remote_library_service | RemoteLibraryService | PRODUCTIVE | passive | 1 | 0 | 0 | 1 | 2 |
| michi_link_server_service | MicroServerService | PRODUCTIVE | passive | 3 | 0 | 0 | 5 | 3 |
| michi_link_track_identity_service | TrackIdentityService | PRODUCTIVE | passive | 2 | 0 | 0 | 1 | 1 |
| mix_query_service | MixQueryService | UNTESTED_VERTICAL | managed | 2 | 0 | 0 | 0 | 0 |
| mix_service | MixService | PRODUCTIVE | managed | 1 | 3 | 5 | 3 | 3 |
| mobile_sync_service | MobileSyncService | PRODUCTIVE | managed | 1 | 3 | 0 | 2 | 4 |
| mpd_service_manager | unknown | UNTESTED_VERTICAL | passive | 0 | 1 | 0 | 0 | 0 |
| mpris_adapter | MPRISAdapter | UNTESTED_VERTICAL | external | 0 | 0 | 0 | 1 | 0 |
| navigation_service | NavigationService | PRODUCTIVE | passive | 2 | 3 | 3 | 1 | 1 |
| notification_action_service | NotificationActionService | PRODUCTIVE | managed | 1 | 2 | 0 | 0 | 3 |
| notification_service | NotificationService | PRODUCTIVE | managed | 1 | 3 | 0 | 1 | 2 |
| output_profile_service | OutputProfileService | PRODUCTIVE | managed | 1 | 0 | 0 | 0 | 3 |
| page_state_store | unknown | UNTESTED_VERTICAL | passive | 0 | 10 | 0 | 0 | 0 |
| paths | unknown | UNTESTED_VERTICAL | passive | 0 | 6 | 0 | 0 | 0 |
| playback_service | PlayerService | PRODUCTIVE | managed | 5 | 11 | 12 | 9 | 2 |
| playback_snapshot_service | PlaybackSnapshotService | PRODUCTIVE | managed | 2 | 0 | 0 | 1 | 4 |
| player_bar_service | PlayerBarService | PRODUCTIVE | managed | 1 | 0 | 0 | 1 | 2 |
| playlist_service | PlaylistService | PRODUCTIVE | managed | 3 | 4 | 9 | 3 | 4 |
| process_controller | ProcessController | PRODUCTIVE | managed | 0 | 4 | 0 | 0 | 2 |
| provider_manager | unknown | UNTESTED_VERTICAL | passive | 1 | 0 | 0 | 0 | 0 |
| query_executor | QueryExecutor | PRODUCTIVE | managed | 0 | 10 | 0 | 2 | 5 |
| queue_service | QueueService | PRODUCTIVE | managed | 3 | 8 | 8 | 10 | 4 |
| radio_service | RadioService | PRODUCTIVE | managed | 1 | 7 | 0 | 4 | 4 |
| read_connection_factory | ReadConnectionFactory | UNTESTED_VERTICAL | passive | 1 | 1 | 0 | 2 | 0 |
| recognition_service | RecognitionService | UNTESTED_VERTICAL | managed | 2 | 0 | 0 | 0 | 0 |
| route_registry_bridge | unknown | UNTESTED_VERTICAL | passive | 0 | 2 | 0 | 0 | 0 |
| runtime_persistence | RuntimePersistence | UNTESTED_VERTICAL | managed | 0 | 0 | 0 | 1 | 0 |
| search_provider_registry | SearchProviderRegistry | PRODUCTIVE | passive | 1 | 0 | 0 | 0 | 3 |
| selection_context_bridge | unknown | UNTESTED_VERTICAL | passive | 0 | 2 | 0 | 0 | 0 |
| settings_coordinator | SettingsRuntimeCoordinator | PRODUCTIVE | managed | 2 | 3 | 0 | 0 | 2 |
| settings_manager | unknown | UNTESTED_VERTICAL | passive | 0 | 3 | 0 | 0 | 0 |
| settings_service | SettingsService | PRODUCTIVE | managed | 1 | 4 | 6 | 1 | 2 |
| smart_tagging_service | SmartTaggingService | UNTESTED_VERTICAL | managed | 0 | 4 | 0 | 1 | 0 |
| snapcast_control | SnapcastJsonRpcClient | UNTESTED_VERTICAL | external | 1 | 0 | 0 | 1 | 0 |
| snapserver_manager | SnapServerManager | UNTESTED_VERTICAL | managed | 2 | 1 | 0 | 1 | 0 |
| songs_service | SongsService | UNTESTED_VERTICAL | managed | 1 | 2 | 0 | 1 | 0 |
| theme_service | ThemeService | PRODUCTIVE | managed | 0 | 2 | 0 | 3 | 2 |
| track_action_service | TrackActionService | PRODUCTIVE | managed | 0 | 4 | 12 | 1 | 1 |
| track_repository | TrackRepository | UNTESTED_VERTICAL | passive | 1 | 0 | 0 | 0 | 0 |
| track_service | TrackService | UNTESTED_VERTICAL | managed | 1 | 2 | 0 | 0 | 0 |
| undo_service | UndoService | PRODUCTIVE | managed | 3 | 0 | 0 | 0 | 3 |
| worker_manager | WorkerManager | PRODUCTIVE | managed | 6 | 15 | 0 | 4 | 8 |
| writer_coordinator | WriterCoordinator | UNTESTED_VERTICAL | managed | 0 | 0 | 0 | 1 | 0 |
