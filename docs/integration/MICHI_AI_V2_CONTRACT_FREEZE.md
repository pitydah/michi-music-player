# Michi AI V2 — Contract Freeze

**SHA:** `HEAD` (see git log)
**Branch:** `michi-ai-functional-v2`
**Date:** 2026-07-14
**Status:** FROZEN — no breaking changes without review

---

## Frozen Elements

### Tool IDs (85 total)
search_library, get_track_details, get_album_details, get_artist_details, list_recent_tracks, list_unplayed_tracks, list_favorites, find_metadata_gaps, play_track, play_album, play_artist, play_playlist, pause, resume, stop, next, previous, seek, set_volume, set_repeat, set_shuffle, get_queue, add_to_queue, play_next, replace_queue, remove_from_queue, clear_queue, reorder_queue, list_playlists, get_playlist, draft_playlist, create_playlist, add_to_playlist, remove_from_playlist, reorder_playlist, delete_playlist, create_smart_mix, explain_mix, save_mix_as_playlist, cancel_mix_generation, probe_audio, analyze_audio, recommend_conversion_profile, preview_conversion, start_conversion, cancel_conversion, analyze_replaygain, check_integrity, compare_audio, inspect_metadata, suggest_metadata_changes, scan_library_health, preview_library_repair, apply_library_repair, rollback_library_repair, list_devices, get_device_details, plan_device_sync, start_device_sync, cancel_device_sync, get_sync_status, diagnose_ecosystem, diagnose_micro_server, diagnose_home_audio, diagnose_pairing, get_setting, list_settings, suggest_setting_change, preview_setting_change, apply_setting_change, restore_setting, navigate, enqueue, device_sync, settings_navigation, diagnostics_open, route_navigation, mix_generate, playlist_create, audio_analysis, metadata_preview

### Plan Schema
- ActionPlan: plan_id, session_id, title, description, intent, steps (tuple[PlanStep]), preconditions, postconditions, risks, warnings, requires_confirmation, confirmation_scope, rollback_strategy, estimated_cost, estimated_duration, created_at, expires_at
- PlanStep: step_id, tool, arguments, depends_on, preconditions, expected_result, on_failure, rollback, timeout, cancellable, compensate

### Result States (15)
CREATED, VALIDATING, AWAITING_CONFIRMATION, QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED, ROLLING_BACK, ROLLED_BACK, SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED

### Gateway Protocols (11)
PlaybackGateway, QueueGateway, LibraryGateway, PlaylistGateway, AudioLabGateway, DeviceGateway, SettingsGateway, DiagnosticsGateway, NavigationRequestGateway, MixGateway, JobGateway

### Error Codes (24)
OK, NO_MATCH, AMBIGUOUS_INTENT, INVALID_ARGUMENTS, CAPABILITY_UNAVAILABLE, TOOL_NOT_FOUND, TOOL_UNAVAILABLE, TOOL_TIMEOUT, TOOL_CANCELLED, TOOL_FAILED, CONFIRMATION_REQUIRED, CONFIRMATION_EXPIRED, PLAN_INVALID, PLAN_STEP_FAILED, PLAN_CANCELLED, ROLLBACK_SUCCEEDED, ROLLBACK_FAILED, PROVIDER_UNAVAILABLE, PROVIDER_TIMEOUT, PROVIDER_INVALID_RESPONSE, CONTEXT_REJECTED, PRIVACY_BLOCKED, SESSION_NOT_FOUND, INTERNAL_ERROR

### Confirmation Modes (5)
NONE, SOFT, EXPLICIT, DESTRUCTIVE, IRREVERSIBLE

### Public Methods (12)
register_gateway, register_gateways, initialize, process_message, confirm_plan, cancel_plan, cancel_execution, get_suggestions, dismiss_suggestion, get_session, create_session, clear_history, get_tools
