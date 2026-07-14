# Michi AI Core V2 — Tool Migration Matrix

## Status Definitions

| Status | Meaning |
|--------|---------|
| `MIGRATED` | Registered in ToolRegistryV2 with full definition (schema, capability, permission, handler) |
| `ADAPTED` | Uses legacy adapter but is reachable via V2 |
| `DEPRECATED` | Duplicate name, alias, or superseded |
| `UNIMPLEMENTED` | Definition exists but no gateway handler |
| `BLOCKED_BY_GATEWAY` | Definition exists, handler needs real gateway |
| `REMOVED` | Intentional removal (fake success, dead code) |

---

## Complete Tool Matrix

### Library Domain (Gateway: `LibraryGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `search_library` | `integrations/ai_assistant/tools/library_tools.py` | integrations | `MIGRATED` | query, limit | library.search | READ_ONLY | no | no | yes | 15s | yes | — | no |
| `get_track_details` | — (new in V2) | none | `MIGRATED` | track_id | library.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `get_album_details` | — (new in V2) | none | `MIGRATED` | album_id | library.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `get_artist_details` | — (new in V2) | none | `MIGRATED` | artist_id | library.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `list_recent_tracks` | — (new in V2) | none | `MIGRATED` | limit | library.read, history.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `list_unplayed_tracks` | — (new in V2) | none | `MIGRATED` | limit | library.read, history.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `list_favorites` | — (new in V2) | none | `MIGRATED` | limit | library.read, history.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `find_metadata_gaps` | `integrations/ai_assistant/tools/metadata_tools.py` | integrations | `MIGRATED` | limit | metadata.read | READ_ONLY | no | no | yes | 30s | no | — | no |
| `recommend_local_tracks` | `integrations/ai_assistant/tools/library_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `get_library_stats` | `integrations/ai_assistant/tools/stats_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `get_library_health` | `michi_ai/tools/library_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `list_missing_metadata` | `michi_ai/tools/library_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `summarize_current_selection` | `michi_ai/tools/library_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Playback Domain (Gateway: `PlaybackGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `play_track` | `integrations/ai_assistant/tools/queue_tools.py` | integrations | `MIGRATED` | track_id | playback.control | PLAYBACK_CONTROL | no | no | no | 10s | no | — | no |
| `play_album` | — (new in V2) | none | `MIGRATED` | album_id, artist, album | playback.control | PLAYBACK_CONTROL | no | no | no | 10s | no | — | no |
| `play_artist` | — (new in V2) | none | `MIGRATED` | artist | playback.control | PLAYBACK_CONTROL | no | no | no | 10s | no | — | no |
| `pause` | — (new in V2) | none | `MIGRATED` | — | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |
| `resume` | — (new in V2) | none | `MIGRATED` | — | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |
| `stop` | — (new in V2) | none | `MIGRATED` | — | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |
| `next` | — (new in V2) | none | `MIGRATED` | — | playback.control | PLAYBACK_CONTROL | no | no | no | 5s | no | — | no |
| `previous` | — (new in V2) | none | `MIGRATED` | — | playback.control | PLAYBACK_CONTROL | no | no | no | 5s | no | — | no |
| `seek` | — (new in V2) | none | `MIGRATED` | position_seconds | playback.control | PLAYBACK_CONTROL | no | no | no | 5s | no | — | no |
| `set_volume` | — (new in V2) | none | `MIGRATED` | volume (0-100) | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |
| `set_repeat` | — (new in V2) | none | `MIGRATED` | mode (none/one/all) | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |
| `set_shuffle` | — (new in V2) | none | `MIGRATED` | enabled | playback.control | PLAYBACK_CONTROL | no | no | yes | 5s | no | — | no |

### Queue Domain (Gateway: `QueueGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `get_queue` | — (new in V2) | none | `MIGRATED` | — | queue.read | READ_ONLY | no | no | yes | 5s | no | — | no |
| `add_to_queue` | `integrations/ai_assistant/tools/queue_tools.py` | integrations | `MIGRATED` | track_ids | queue.modify | PLAYBACK_CONTROL | no | no | yes | 10s | no | — | no |
| `play_next` | — (new in V2) | none | `MIGRATED` | track_ids | queue.modify | PLAYBACK_CONTROL | no | no | yes | 10s | no | — | no |
| `replace_queue` | — (new in V2) | none | `MIGRATED` | track_ids | queue.modify | PLAYBACK_CONTROL | YES | no | no | 10s | no | — | no |
| `remove_from_queue` | — (new in V2) | none | `MIGRATED` | position | queue.modify | PLAYBACK_CONTROL | no | no | no | 5s | no | — | no |
| `clear_queue` | — (new in V2) | none | `MIGRATED` | — | queue.modify | PLAYBACK_CONTROL | YES | no | yes | 5s | no | — | no |
| `reorder_queue` | — (new in V2) | none | `MIGRATED` | from_position, to_position | queue.modify | PLAYBACK_CONTROL | no | no | no | 5s | no | — | no |

### Playlist Domain (Gateway: `PlaylistGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `list_playlists` | — (new in V2) | none | `MIGRATED` | — | playlist.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `get_playlist` | — (new in V2) | none | `MIGRATED` | playlist_id | playlist.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `draft_playlist` | `integrations/ai_assistant/tools/playlist_tools.py` | integrations | `MIGRATED` | description, limit | playlist.read | READ_ONLY | no | no | yes | 20s | no | — | no |
| `create_playlist` | `integrations/ai_assistant/tools/playlist_tools.py` | integrations | `MIGRATED` | name, track_ids | playlist.modify | LIBRARY_MUTATION | no | no | no | 15s | no | — | no |
| `add_to_playlist` | — (new in V2) | none | `MIGRATED` | playlist_id, track_ids | playlist.modify | LIBRARY_MUTATION | no | no | yes | 15s | no | — | no |
| `remove_from_playlist` | — (new in V2) | none | `MIGRATED` | playlist_id, position | playlist.modify | LIBRARY_MUTATION | no | no | no | 10s | no | — | no |
| `reorder_playlist` | — (new in V2) | none | `MIGRATED` | playlist_id, from/to pos | playlist.modify | LIBRARY_MUTATION | no | no | no | 10s | no | — | no |
| `delete_playlist` | — (new in V2) | none | `MIGRATED` | playlist_id | playlist.modify | DESTRUCTIVE | YES | yes | yes | 10s | no | — | no |
| `create_playlist_from_selection` | `michi_ai/tools/playlist_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `create_playlist_from_draft` | `integrations/ai_assistant/tools/playlist_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `queue_selection` | `michi_ai/tools/playlist_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `save_recommendation_as_playlist` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Mix Domain (Gateway: `MixGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `create_smart_mix` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `MIGRATED` | strategy, genre, decade | mix.generate | READ_ONLY | no | no | no | 30s | yes | — | no |
| `explain_mix` | — (new in V2) | none | `MIGRATED` | mix_id | mix.generate | READ_ONLY | no | no | yes | 15s | no | — | no |
| `save_mix_as_playlist` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `MIGRATED` | mix_id, name | playlist.modify | LIBRARY_MUTATION | no | no | no | 15s | no | — | no |
| `cancel_mix_generation` | — (new in V2) | none | `MIGRATED` | job_id | mix.generate | READ_ONLY | no | no | yes | 5s | no | — | no |
| `recommend_music` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `recommend_from_track` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `recommend_from_artist` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `recommend_from_album` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `recommend_from_genre` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `create_acoustic_mix` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `explain_recommendation` | `integrations/ai_assistant/tools/recommendation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Audio Lab Domain (Gateway: `AudioLabGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `probe_audio` | — (new in V2) | none | `MIGRATED` | track_id | audio_lab.analyze | READ_ONLY | no | no | yes | 15s | no | — | no |
| `analyze_audio` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | integrations | `MIGRATED` | track_ids | audio_lab.analyze | READ_ONLY | no | no | no | 120s | yes | — | no |
| `recommend_conversion_profile` | `integrations/ai_assistant/tools/audio_conversion_tools.py` | none | `MIGRATED` | track_ids, target | audio_lab.analyze | READ_ONLY | no | no | yes | 15s | no | — | no |
| `preview_conversion` | — (new in V2) | none | `MIGRATED` | plan_id | audio_lab.convert | READ_ONLY | no | no | yes | 15s | no | — | no |
| `start_conversion` | — (new in V2) | none | `MIGRATED` | plan_id | audio_lab.convert | LIBRARY_MUTATION | YES | no | no | 30s | yes | — | no |
| `cancel_conversion` | — (new in V2) | none | `MIGRATED` | job_id | audio_lab.convert | LIBRARY_MUTATION | no | no | yes | 10s | no | — | no |
| `analyze_replaygain` | — (new in V2) | none | `MIGRATED` | track_ids | audio_lab.replaygain | READ_ONLY | no | no | yes | 60s | yes | — | no |
| `check_integrity` | — (new in V2) | none | `MIGRATED` | track_ids | audio_lab.analyze | READ_ONLY | no | no | yes | 120s | yes | — | no |
| `compare_audio` | — (new in V2) | none | `MIGRATED` | track_id_a, track_id_b | audio_lab.analyze | READ_ONLY | no | no | yes | 30s | no | — | no |
| `get_audio_analysis_status` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | both | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `analyze_selected_tracks` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `find_sonically_similar` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `explain_acoustic_features` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `list_tracks_missing_features` | `integrations/ai_assistant/tools/audio_analysis_tools.py` | both | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Metadata Domain (Gateway: `LibraryGateway` + `MetadataGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `inspect_metadata` | — (new in V2) | none | `MIGRATED` | track_id | metadata.read | READ_ONLY | no | no | yes | 15s | no | — | no |
| `suggest_metadata_changes` | — (new in V2) | none | `MIGRATED` | track_id, album_id | metadata.read | READ_ONLY | no | no | yes | 20s | no | — | no |
| `mark_favorite` | `integrations/ai_assistant/tools/favorite_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `unmark_favorite` | `integrations/ai_assistant/tools/favorite_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `lookup_artist_info` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `lookup_album_info` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `lookup_track_info` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `explain_artist` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `explain_album` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `refresh_artist_metadata` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `refresh_album_metadata` | `integrations/ai_assistant/tools/knowledge_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `find_metadata_inconsistencies` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_metadata_for_track` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_metadata_for_album` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_metadata_for_artist` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `create_metadata_review` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `apply_metadata_review` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `reject_metadata_review` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `undo_metadata_review` | `integrations/ai_assistant/tools/metadata_review_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `explain_audio_format` | `integrations/ai_assistant/tools/audio_conversion_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_mobile_audio_profile` | `integrations/ai_assistant/tools/audio_conversion_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_micro_server_streaming_profile` | `integrations/ai_assistant/tools/audio_conversion_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `suggest_hifi_audio_profile` | `integrations/ai_assistant/tools/audio_conversion_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Library Doctor Domain (Gateway: `DiagnosticsGateway` + `LibraryDoctorGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `scan_library_health` | — (new in V2) | none | `MIGRATED` | — | library_doctor.scan | READ_ONLY | no | no | no | 120s | yes | — | no |
| `preview_library_repair` | — (new in V2) | none | `MIGRATED` | scan_id | library_doctor.scan | READ_ONLY | no | no | yes | 30s | no | — | no |
| `apply_library_repair` | — (new in V2) | none | `MIGRATED` | repair_id | library_doctor.repair | DESTRUCTIVE | YES | yes | no | 300s | yes | `rollback_library_repair` | no |
| `rollback_library_repair` | — (new in V2) | none | `MIGRATED` | repair_id | library_doctor.repair | DESTRUCTIVE | YES | yes | no | 300s | no | — | no |

### Devices & Sync Domain (Gateway: `DeviceGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `list_devices` | — (new in V2) | none | `MIGRATED` | — | devices.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `get_device_details` | — (new in V2) | none | `MIGRATED` | device_id | devices.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `plan_device_sync` | — (new in V2) | none | `MIGRATED` | playlist_id, device_id | devices.sync | READ_ONLY | no | no | yes | 15s | no | — | no |
| `start_device_sync` | — (new in V2) | none | `MIGRATED` | plan_id | devices.sync | DEVICE_TRANSFER | YES | no | no | 30s | yes | — | no |
| `cancel_device_sync` | — (new in V2) | none | `MIGRATED` | job_id | devices.sync | DEVICE_TRANSFER | no | no | yes | 10s | no | — | no |
| `get_sync_status` | `michi_ai/tools/sync_tools.py` | michi_ai | `MIGRATED` | — | devices.read | READ_ONLY | no | no | yes | 10s | no | — | **FIXED** |
| `list_sync_peers` | `michi_ai/tools/sync_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | **fake success** |
| `discover_micro_server` | `michi_ai/tools/michi_link_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Ecosystem & Connections Domain (Gateway: `DeviceGateway` + `DiagnosticsGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `diagnose_ecosystem` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `MIGRATED` | — | diagnostics.read | READ_ONLY | no | no | no | 60s | yes | — | no |
| `diagnose_micro_server` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `MIGRATED` | host, port | diagnostics.read | READ_ONLY | no | no | yes | 30s | no | — | no |
| `diagnose_home_audio` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `MIGRATED` | — | diagnostics.read | READ_ONLY | no | no | yes | 30s | no | — | no |
| `diagnose_pairing` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `MIGRATED` | — | diagnostics.read | READ_ONLY | no | no | yes | 30s | no | — | no |
| `suggest_ecosystem_fix` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `BLOCKED_BY_GATEWAY` | — | — | — | — | — | — | — | — | — | — |
| `create_ecosystem_config_plan` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `BLOCKED_BY_GATEWAY` | — | — | — | — | — | — | — | — | — | — |
| `preview_ecosystem_config_plan` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `BLOCKED_BY_GATEWAY` | — | — | — | — | — | — | — | — | — | — |
| `apply_ecosystem_config_plan` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `BLOCKED_BY_GATEWAY` | — | — | — | — | — | — | — | — | — | — |
| `rollback_ecosystem_config_plan` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `BLOCKED_BY_GATEWAY` | — | — | — | — | — | — | — | — | — | — |
| `diagnose_mobile_sync` | `integrations/ai_assistant/tools/ecosystem_tools.py` | none | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `get_michi_link_status` | `michi_ai/tools/michi_link_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | **fake success** |

### Settings Domain (Gateway: `SettingsGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `get_setting` | — (new in V2) | none | `MIGRATED` | key | settings.read | READ_ONLY | no | no | yes | 5s | no | — | no |
| `list_settings` | — (new in V2) | none | `MIGRATED` | — | settings.read | READ_ONLY | no | no | yes | 5s | no | — | no |
| `suggest_setting_change` | — (new in V2) | none | `MIGRATED` | key, value | settings.read | READ_ONLY | no | no | yes | 10s | no | — | no |
| `preview_setting_change` | — (new in V2) | none | `MIGRATED` | key, value | settings.read | READ_ONLY | no | no | yes | 5s | no | — | no |
| `apply_setting_change` | — (new in V2) | none | `MIGRATED` | key, value | settings.modify | SETTINGS_MUTATION | YES | no | no | 10s | no | — | no |
| `restore_setting` | — (new in V2) | none | `MIGRATED` | key | settings.modify | SETTINGS_MUTATION | YES | no | yes | 10s | no | — | no |
| `list_config_plans` | `michi_ai/tools/config_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | **fake success** |
| `create_config_plan` | `michi_ai/tools/config_tools.py` | michi_ai | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

### Navigation Domain (Gateway: `NavigationRequestGateway`)

| Tool | File | Legacy Registry | V2 Status | Schema | Capability | Permission | Confirmation | Destructive | Idempotent | Timeout | Cancellable | Rollback | Fake Success |
|------|------|----------------|-----------|--------|------------|------------|--------------|-------------|------------|---------|-------------|----------|--------------|
| `navigate` | — (new in V2) | none | `MIGRATED` | route, params | navigation.request | READ_ONLY | no | no | yes | 5s | no | — | no |
| `open_artist_view` | `integrations/ai_assistant/tools/navigation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `open_album_view` | `integrations/ai_assistant/tools/navigation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `open_genre_view` | `integrations/ai_assistant/tools/navigation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `open_playlist_view` | `integrations/ai_assistant/tools/navigation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |
| `show_track_in_library` | `integrations/ai_assistant/tools/navigation_tools.py` | integrations | `DEPRECATED` | — | — | — | — | — | — | — | — | — | — |

---

## Summary

| Status | Count |
|--------|-------|
| **MIGRATED** | 60 |
| **DEPRECATED** | 44 |
| **BLOCKED_BY_GATEWAY** | 5 |
| **REMOVED (fake success)** | 4 (get_sync_status fixed, list_sync_peers, get_michi_link_status, list_config_plans deprecated) |
| **Total active tools** | 60 |

## Migration Rules Applied

1. All 60 active tools registered in `ToolRegistryV2` via `register_builtin_tools()`
2. Each declares: `input_schema`, `output_schema`, `capability`, `permission`, `requires_confirmation`, `destructive`, `idempotent`, `timeout_seconds`, `cancellable`, `rollback_tool`
3. Tools with `requires_confirmation=True`: replace_queue, clear_queue, delete_playlist, start_conversion, apply_library_repair, rollback_library_repair, start_device_sync, apply_setting_change, restore_setting
4. Fake successes from legacy `michi_ai/tools/*` are addressed: those tools are deprecated; the V2 replacements use gateways that properly report capability unavailability
5. Legacy adapter (`OperationResultToLegacyToolResultAdapter`) exists for temporary compatibility
6. Duplicate names resolved: canonical name selected, legacy version deprecated
