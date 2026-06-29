"""Event types for the context system — internal, serializable events."""


class AppEvent:
    APP_STARTED = "app_started"
    APP_CLOSED = "app_closed"
    SECTION_CHANGED = "section_changed"
    LIBRARY_TAB_CHANGED = "library_tab_changed"
    TRACK_SELECTED = "track_selected"
    SELECTION_CHANGED = "selection_changed"
    TRACK_PLAYED = "track_played"
    TRACK_PAUSED = "track_paused"
    TRACK_FAVORITED = "track_favorited"
    TRACK_UNFAVORITED = "track_unfavorited"
    SCAN_STARTED = "scan_started"
    SCAN_FINISHED = "scan_finished"
    METADATA_REPAIR_STARTED = "metadata_repair_started"
    METADATA_REPAIR_FINISHED = "metadata_repair_finished"
    AUDIO_ANALYSIS_FINISHED = "audio_analysis_finished"
    MIX_PREVIEW_GENERATED = "mix_preview_generated"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    SYNC_STARTED = "sync_started"
    SYNC_FINISHED = "sync_finished"
    ASSISTANT_OPENED = "assistant_opened"
    ASSISTANT_ACTION_CONFIRMED = "assistant_action_confirmed"

    # Library lifecycle
    LIBRARY_RELOADED = "library_reloaded"
    IMPORT_STARTED = "import_started"
    IMPORT_FINISHED = "import_finished"

    # Metadata
    METADATA_SAVED = "metadata_saved"

    # Playback / Now Playing
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_STOPPED = "playback_stopped"
    NOW_PLAYING_UPDATED = "now_playing_updated"
    QUALITY_UPDATED = "quality_updated"
    AUDIO_ROUTE_CHANGED = "audio_route_changed"

    # Queue
    QUEUE_UPDATED = "queue_updated"
    QUEUE_CLEARED = "queue_cleared"
    TRACK_QUEUED = "track_queued"
    PLAYBACK_MODE_CHANGED = "playback_mode_changed"

    # Playlist
    PLAYLIST_OPENED = "playlist_opened"
    PLAYLIST_CREATED = "playlist_created"
    PLAYLIST_DELETED = "playlist_deleted"
    PLAYLIST_PLAYED = "playlist_played"
    PLAYLIST_QUEUED = "playlist_queued"
    PLAYLIST_IMPORTED = "playlist_imported"
    PLAYLIST_EXPORTED = "playlist_exported"
    TRACK_ADDED_TO_PLAYLIST = "track_added_to_playlist"

    # Mix / Smart views
    MIX_OPENED = "mix_opened"
    MIX_PLAYED = "mix_played"
    MIX_QUEUED = "mix_queued"

    # Folder browser
    FOLDER_SELECTED = "folder_selected"
    FOLDER_SCANNED = "folder_scanned"
    FOLDER_QUEUED = "folder_queued"

    # Search
    SEARCH_STARTED = "search_started"
    SEARCH_PERFORMED = "search_performed"
    SEARCH_CLEARED = "search_cleared"

    # Metadata extended
    METADATA_REVIEW_OPENED = "metadata_review_opened"
    COVER_UPDATED = "cover_updated"
    LYRICS_UPDATED = "lyrics_updated"
    TAGS_BATCH_UPDATED = "tags_batch_updated"

    # Audio analysis extended
    AUDIO_ANALYSIS_STARTED = "audio_analysis_started"
    AUDIO_ANALYSIS_FAILED = "audio_analysis_failed"
    AUDIO_FEATURES_UPDATED = "audio_features_updated"

    # Disc Lab / Ripping
    DISC_DETECTED = "disc_detected"
    RIP_STARTED = "rip_started"
    RIP_FINISHED = "rip_finished"
    RIP_FAILED = "rip_failed"

    # Identifier / Radio
    IDENTIFICATION_STARTED = "identification_started"
    IDENTIFICATION_MATCHED = "identification_matched"
    IDENTIFICATION_FAILED = "identification_failed"
    RADIO_STATION_SELECTED = "radio_station_selected"
    RADIO_PLAYED = "radio_played"

    # Operational errors
    CONTEXT_ERROR_RECORDED = "context_error_recorded"
