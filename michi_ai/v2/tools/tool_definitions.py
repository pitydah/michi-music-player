from __future__ import annotations

from michi_ai.v2.core.models import (
    PermissionLevel, ToolDefinition,
)


def _schema(required: list[str] | None = None, properties: dict | None = None, additional: bool = True) -> dict:
    return {
        "required": required or [],
        "properties": properties or {},
        "additionalProperties": additional,
    }


SHARED_TRACK_ID_SCHEMA = _schema(
    required=["track_id"],
    properties={"track_id": {"type": "string", "description": "Track ID"}},
)
SHARED_QUERY_SCHEMA = _schema(
    required=["query"],
    properties={"query": {"type": "string"}, "limit": {"type": "integer"}},
)
SHARED_VOLUME_SCHEMA = _schema(
    required=["volume"],
    properties={"volume": {"type": "integer", "minimum": 0, "maximum": 100}},
)

BUILTIN_TOOL_DEFINITIONS: list[ToolDefinition] = [
    # == Library ==
    ToolDefinition(
        name="search_library", version="2.0.0",
        description="Search the music library by text query with optional field filters",
        input_schema=SHARED_QUERY_SCHEMA,
        output_schema=_schema(properties={"results": {"type": "array"}, "total": {"type": "integer"}}),
        permission=PermissionLevel.READ_ONLY,
        capabilities=("library.search",),
        idempotent=True, cancellable=True, timeout_seconds=15,
        tags=("library", "search"),
    ),
    ToolDefinition(
        name="get_track_details", version="2.0.0",
        description="Get detailed information about a specific track",
        input_schema=_schema(required=["track_id"], properties={"track_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="get_album_details", version="2.0.0",
        description="Get detailed information about an album",
        input_schema=_schema(required=["album_id"], properties={"album_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="get_artist_details", version="2.0.0",
        description="Get detailed information about an artist",
        input_schema=_schema(required=["artist_id"], properties={"artist_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="list_recent_tracks", version="2.0.0",
        description="List recently played tracks",
        input_schema=_schema(properties={"limit": {"type": "integer", "default": 20}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read", "history.read"),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="list_unplayed_tracks", version="2.0.0",
        description="List tracks that have never been played",
        input_schema=_schema(properties={"limit": {"type": "integer", "default": 20}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read", "history.read"),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="list_favorites", version="2.0.0",
        description="List favorite tracks",
        input_schema=_schema(properties={"limit": {"type": "integer", "default": 20}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library.read", "history.read"),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="find_metadata_gaps", version="2.0.0",
        description="Find tracks with missing or incomplete metadata",
        input_schema=_schema(properties={"limit": {"type": "integer", "default": 50}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=30,
    ),

    # == Playback ==
    ToolDefinition(
        name="play_track", version="2.0.0",
        description="Play a specific track",
        input_schema=_schema(required=["track_id"], properties={"track_id": {"type": "string"}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="play_album", version="2.0.0",
        description="Play an album",
        input_schema=_schema(properties={"album_id": {"type": "string"}, "artist": {"type": "string"}, "album": {"type": "string"}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="play_artist", version="2.0.0",
        description="Play tracks by an artist",
        input_schema=_schema(required=["artist"], properties={"artist": {"type": "string"}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="pause", version="2.0.0",
        description="Pause current playback",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="resume", version="2.0.0",
        description="Resume paused playback",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="stop", version="2.0.0",
        description="Stop playback",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="next", version="2.0.0",
        description="Skip to the next track",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=5,
    ),
    ToolDefinition(
        name="previous", version="2.0.0",
        description="Go back to the previous track",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=5,
    ),
    ToolDefinition(
        name="seek", version="2.0.0",
        description="Seek to a position in the current track",
        input_schema=_schema(required=["position_seconds"], properties={"position_seconds": {"type": "number", "minimum": 0}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=False, timeout_seconds=5,
    ),
    ToolDefinition(
        name="set_volume", version="2.0.0",
        description="Set the playback volume",
        input_schema=SHARED_VOLUME_SCHEMA,
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="set_repeat", version="2.0.0",
        description="Set repeat mode",
        input_schema=_schema(required=["mode"], properties={"mode": {"type": "string", "enum": ["none", "one", "all"]}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="set_shuffle", version="2.0.0",
        description="Enable or disable shuffle mode",
        input_schema=_schema(required=["enabled"], properties={"enabled": {"type": "boolean"}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("playback.control",),
        idempotent=True, timeout_seconds=5,
    ),

    # == Queue ==
    ToolDefinition(
        name="get_queue", version="2.0.0",
        description="Get the current playback queue",
        permission=PermissionLevel.READ_ONLY, capabilities=("queue.read",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="add_to_queue", version="2.0.0",
        description="Add tracks to the end of the queue",
        input_schema=_schema(required=["track_ids"], properties={"track_ids": {"type": "array", "maxItems": 200}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="play_next", version="2.0.0",
        description="Add tracks to play next in the queue",
        input_schema=_schema(required=["track_ids"], properties={"track_ids": {"type": "array", "maxItems": 50}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="replace_queue", version="2.0.0",
        description="Replace the entire queue with new tracks",
        input_schema=_schema(required=["track_ids"], properties={"track_ids": {"type": "array", "maxItems": 500}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        requires_confirmation=True, destructive=False, idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="remove_from_queue", version="2.0.0",
        description="Remove a track from the queue by position",
        input_schema=_schema(required=["position"], properties={"position": {"type": "integer", "minimum": 0}}),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        idempotent=False, timeout_seconds=5,
    ),
    ToolDefinition(
        name="clear_queue", version="2.0.0",
        description="Clear the entire playback queue",
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        requires_confirmation=True, destructive=False, idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="reorder_queue", version="2.0.0",
        description="Reorder tracks in the queue",
        input_schema=_schema(
            required=["from_position", "to_position"],
            properties={"from_position": {"type": "integer"}, "to_position": {"type": "integer"}},
        ),
        permission=PermissionLevel.PLAYBACK_CONTROL, capabilities=("queue.modify",),
        idempotent=False, timeout_seconds=5,
    ),

    # == Playlists ==
    ToolDefinition(
        name="list_playlists", version="2.0.0",
        description="List all playlists",
        permission=PermissionLevel.READ_ONLY, capabilities=("playlist.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="get_playlist", version="2.0.0",
        description="Get a playlist by ID",
        input_schema=_schema(required=["playlist_id"], properties={"playlist_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("playlist.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="draft_playlist", version="2.0.0",
        description="Draft a playlist from a description without saving",
        input_schema=_schema(required=["description"], properties={"description": {"type": "string"}, "limit": {"type": "integer", "default": 30}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("playlist.read",),
        idempotent=True, timeout_seconds=20,
    ),
    ToolDefinition(
        name="create_playlist", version="2.0.0",
        description="Create a new playlist",
        input_schema=_schema(
            required=["name"],
            properties={"name": {"type": "string", "maxLength": 200}, "track_ids": {"type": "array", "maxItems": 500}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("playlist.modify",),
        requires_confirmation=False, destructive=False, idempotent=False, timeout_seconds=15,
    ),
    ToolDefinition(
        name="add_to_playlist", version="2.0.0",
        description="Add tracks to an existing playlist",
        input_schema=_schema(
            required=["playlist_id", "track_ids"],
            properties={"playlist_id": {"type": "string"}, "track_ids": {"type": "array", "maxItems": 200}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("playlist.modify",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="remove_from_playlist", version="2.0.0",
        description="Remove a track from a playlist by position",
        input_schema=_schema(
            required=["playlist_id", "position"],
            properties={"playlist_id": {"type": "string"}, "position": {"type": "integer"}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("playlist.modify",),
        idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="reorder_playlist", version="2.0.0",
        description="Reorder tracks in a playlist",
        input_schema=_schema(
            required=["playlist_id", "from_position", "to_position"],
            properties={"playlist_id": {"type": "string"}, "from_position": {"type": "integer"}, "to_position": {"type": "integer"}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("playlist.modify",),
        idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="delete_playlist", version="2.0.0",
        description="Delete a playlist permanently",
        input_schema=_schema(required=["playlist_id"], properties={"playlist_id": {"type": "string"}}),
        permission=PermissionLevel.DESTRUCTIVE, capabilities=("playlist.modify",),
        requires_confirmation=True, destructive=True, idempotent=True, timeout_seconds=10,
    ),

    # == Mix ==
    ToolDefinition(
        name="create_smart_mix", version="2.0.0",
        description="Create a smart mix based on criteria",
        input_schema=_schema(
            properties={
                "strategy": {"type": "string"}, "genre": {"type": "string"},
                "decade": {"type": "string"}, "seed_track_id": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
            },
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("mix.generate",),
        cancellable=True, idempotent=False, timeout_seconds=30,
    ),
    ToolDefinition(
        name="explain_mix", version="2.0.0",
        description="Explain the reasoning behind a mix",
        input_schema=_schema(required=["mix_id"], properties={"mix_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("mix.generate",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="save_mix_as_playlist", version="2.0.0",
        description="Save a generated mix as a permanent playlist",
        input_schema=_schema(
            required=["mix_id", "name"],
            properties={"mix_id": {"type": "string"}, "name": {"type": "string", "maxLength": 200}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("playlist.modify",),
        idempotent=False, timeout_seconds=15,
    ),
    ToolDefinition(
        name="cancel_mix_generation", version="2.0.0",
        description="Cancel an ongoing mix generation",
        input_schema=_schema(required=["job_id"], properties={"job_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("mix.generate",),
        idempotent=True, timeout_seconds=5,
    ),

    # == Audio Lab ==
    ToolDefinition(
        name="probe_audio", version="2.0.0",
        description="Probe audio file format and technical details",
        input_schema=SHARED_TRACK_ID_SCHEMA,
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.analyze",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="analyze_audio", version="2.0.0",
        description="Run audio feature analysis on tracks",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 50}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.analyze",),
        cancellable=True, idempotent=False, timeout_seconds=120,
    ),
    ToolDefinition(
        name="recommend_conversion_profile", version="2.0.0",
        description="Recommend an audio conversion profile",
        input_schema=_schema(
            required=["track_ids", "target"],
            properties={
                "track_ids": {"type": "array", "maxItems": 500},
                "target": {"type": "string", "enum": ["mobile", "micro_server", "hifi", "streaming"]},
            },
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.analyze",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="preview_conversion", version="2.0.0",
        description="Preview a conversion before executing it",
        input_schema=_schema(
            required=["plan_id"],
            properties={"plan_id": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.convert",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="start_conversion", version="2.0.0",
        description="Start an audio conversion job",
        input_schema=_schema(
            required=["plan_id"],
            properties={"plan_id": {"type": "string"}},
        ),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("audio_lab.convert",),
        requires_confirmation=True, cancellable=True, idempotent=False, timeout_seconds=30,
    ),
    ToolDefinition(
        name="cancel_conversion", version="2.0.0",
        description="Cancel a running conversion job",
        input_schema=_schema(required=["job_id"], properties={"job_id": {"type": "string"}}),
        permission=PermissionLevel.LIBRARY_MUTATION, capabilities=("audio_lab.convert",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="analyze_replaygain", version="2.0.0",
        description="Analyze ReplayGain values for tracks",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 100}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.replaygain",),
        cancellable=True, idempotent=True, timeout_seconds=60,
    ),
    ToolDefinition(
        name="check_integrity", version="2.0.0",
        description="Check audio file integrity",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 50}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.analyze",),
        cancellable=True, idempotent=True, timeout_seconds=120,
    ),
    ToolDefinition(
        name="compare_audio", version="2.0.0",
        description="Compare two audio files",
        input_schema=_schema(
            required=["track_id_a", "track_id_b"],
            properties={"track_id_a": {"type": "string"}, "track_id_b": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("audio_lab.analyze",),
        idempotent=True, timeout_seconds=30,
    ),

    # == Metadata ==
    ToolDefinition(
        name="inspect_metadata", version="2.0.0",
        description="Inspect complete metadata for a track",
        input_schema=SHARED_TRACK_ID_SCHEMA,
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="suggest_metadata_changes", version="2.0.0",
        description="Suggest metadata improvements for a track or album",
        input_schema=_schema(
            properties={"track_id": {"type": "string"}, "album_id": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=20,
    ),

    ToolDefinition(
        name="inspect_selection", version="2.0.0",
        description="Inspect metadata for a selection of tracks",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 50}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=30,
    ),
    ToolDefinition(
        name="build_proposal", version="2.0.0",
        description="Build a metadata change proposal from track IDs",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 50}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=60,
    ),
    ToolDefinition(
        name="preview_changes", version="2.0.0",
        description="Preview metadata changes from a review",
        input_schema=_schema(
            required=["review_id"],
            properties={"review_id": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="apply_review", version="2.0.0",
        description="Apply a metadata review with confirmation",
        input_schema=_schema(
            required=["review_id", "confirmation_token"],
            properties={"review_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
        ),
        permission=PermissionLevel.DESTRUCTIVE, capabilities=("metadata.modify",),
        requires_confirmation=True, destructive=False, cancellable=True,
        idempotent=False, timeout_seconds=300,
        rollback_tool="rollback_metadata",
    ),
    ToolDefinition(
        name="rollback_metadata", version="2.0.0",
        description="Rollback a metadata operation",
        input_schema=_schema(
            required=["operation_id", "confirmation_token"],
            properties={"operation_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
        ),
        permission=PermissionLevel.DESTRUCTIVE, capabilities=("metadata.modify",),
        requires_confirmation=True, destructive=False,
        idempotent=False, timeout_seconds=300,
    ),
    ToolDefinition(
        name="check_consistency", version="2.0.0",
        description="Check metadata consistency across tracks",
        input_schema=_schema(
            required=["track_ids"],
            properties={"track_ids": {"type": "array", "maxItems": 200}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=60,
    ),
    ToolDefinition(
        name="scan_duplicates", version="2.0.0",
        description="Scan for duplicate metadata entries",
        input_schema=_schema(
            properties={"track_ids": {"type": "array", "maxItems": 200}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("metadata.read",),
        idempotent=True, timeout_seconds=60,
    ),

    # == Library Doctor ==
    ToolDefinition(
        name="scan_library_health", version="2.0.0",
        description="Scan the library for health issues",
        permission=PermissionLevel.READ_ONLY, capabilities=("library_doctor.scan",),
        cancellable=True, idempotent=False, timeout_seconds=120,
    ),
    ToolDefinition(
        name="preview_library_repair", version="2.0.0",
        description="Preview what a library repair would change",
        input_schema=_schema(properties={"scan_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("library_doctor.scan",),
        idempotent=True, timeout_seconds=30,
    ),
    ToolDefinition(
        name="apply_library_repair", version="2.0.0",
        description="Apply suggested library repairs",
        input_schema=_schema(required=["repair_id"], properties={"repair_id": {"type": "string"}}),
        permission=PermissionLevel.DESTRUCTIVE, capabilities=("library_doctor.repair",),
        requires_confirmation=True, destructive=True, cancellable=True, idempotent=False, timeout_seconds=300,
        rollback_tool="rollback_library_repair",
    ),
    ToolDefinition(
        name="rollback_library_repair", version="2.0.0",
        description="Rollback a library repair",
        input_schema=_schema(required=["repair_id"], properties={"repair_id": {"type": "string"}}),
        permission=PermissionLevel.DESTRUCTIVE, capabilities=("library_doctor.repair",),
        requires_confirmation=True, destructive=True, idempotent=False, timeout_seconds=300,
    ),

    # == Devices & Sync ==
    ToolDefinition(
        name="list_devices", version="2.0.0",
        description="List available devices",
        permission=PermissionLevel.READ_ONLY, capabilities=("devices.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="get_device_details", version="2.0.0",
        description="Get details for a specific device",
        input_schema=_schema(required=["device_id"], properties={"device_id": {"type": "string"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("devices.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="plan_device_sync", version="2.0.0",
        description="Plan a sync operation with a device",
        input_schema=_schema(
            required=["playlist_id", "device_id"],
            properties={"playlist_id": {"type": "string"}, "device_id": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("devices.sync",),
        idempotent=True, timeout_seconds=15,
    ),
    ToolDefinition(
        name="start_device_sync", version="2.0.0",
        description="Start a device sync operation",
        input_schema=_schema(required=["plan_id"], properties={"plan_id": {"type": "string"}}),
        permission=PermissionLevel.DEVICE_TRANSFER, capabilities=("devices.sync",),
        requires_confirmation=True, cancellable=True, idempotent=False, timeout_seconds=30,
    ),
    ToolDefinition(
        name="cancel_device_sync", version="2.0.0",
        description="Cancel a running device sync",
        input_schema=_schema(required=["job_id"], properties={"job_id": {"type": "string"}}),
        permission=PermissionLevel.DEVICE_TRANSFER, capabilities=("devices.sync",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="get_sync_status", version="2.0.0",
        description="Get the current sync status",
        permission=PermissionLevel.READ_ONLY, capabilities=("devices.read",),
        idempotent=True, timeout_seconds=10,
    ),

    # == Diagnostics ==
    ToolDefinition(
        name="diagnose_ecosystem", version="2.0.0",
        description="Run full ecosystem diagnostics",
        permission=PermissionLevel.READ_ONLY, capabilities=("diagnostics.read",),
        cancellable=True, idempotent=False, timeout_seconds=60,
    ),
    ToolDefinition(
        name="diagnose_micro_server", version="2.0.0",
        description="Diagnose micro server connectivity",
        input_schema=_schema(properties={"host": {"type": "string"}, "port": {"type": "integer"}}),
        permission=PermissionLevel.READ_ONLY, capabilities=("diagnostics.read",),
        idempotent=True, timeout_seconds=30,
    ),
    ToolDefinition(
        name="diagnose_home_audio", version="2.0.0",
        description="Diagnose home audio system",
        permission=PermissionLevel.READ_ONLY, capabilities=("diagnostics.read",),
        idempotent=True, timeout_seconds=30,
    ),
    ToolDefinition(
        name="diagnose_pairing", version="2.0.0",
        description="Diagnose device pairing",
        permission=PermissionLevel.READ_ONLY, capabilities=("diagnostics.read",),
        idempotent=True, timeout_seconds=30,
    ),

    # == Settings ==
    ToolDefinition(
        name="get_setting", version="2.0.0",
        description="Get a setting value",
        input_schema=_schema(
            required=["key"],
            properties={"key": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("settings.read",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="list_settings", version="2.0.0",
        description="List all available settings",
        permission=PermissionLevel.READ_ONLY, capabilities=("settings.read",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="suggest_setting_change", version="2.0.0",
        description="Suggest a setting change",
        input_schema=_schema(
            required=["key", "value"],
            properties={"key": {"type": "string"}, "value": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("settings.read",),
        idempotent=True, timeout_seconds=10,
    ),
    ToolDefinition(
        name="preview_setting_change", version="2.0.0",
        description="Preview what a setting change would do",
        input_schema=_schema(
            required=["key", "value"],
            properties={"key": {"type": "string"}, "value": {"type": "string"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("settings.read",),
        idempotent=True, timeout_seconds=5,
    ),
    ToolDefinition(
        name="apply_setting_change", version="2.0.0",
        description="Apply a setting change",
        input_schema=_schema(
            required=["key", "value"],
            properties={"key": {"type": "string"}, "value": {"type": "string"}},
        ),
        permission=PermissionLevel.SETTINGS_MUTATION, capabilities=("settings.modify",),
        requires_confirmation=True, destructive=False, idempotent=False, timeout_seconds=10,
    ),
    ToolDefinition(
        name="restore_setting", version="2.0.0",
        description="Restore a setting to its default",
        input_schema=_schema(required=["key"], properties={"key": {"type": "string"}}),
        permission=PermissionLevel.SETTINGS_MUTATION, capabilities=("settings.modify",),
        requires_confirmation=True, idempotent=True, timeout_seconds=10,
    ),

    # == Navigation (no-op, emits request only) ==
    ToolDefinition(
        name="navigate", version="2.0.0",
        description="Request navigation to a section",
        input_schema=_schema(
            required=["route"],
            properties={"route": {"type": "string"}, "params": {"type": "object"}},
        ),
        permission=PermissionLevel.READ_ONLY, capabilities=("navigation.request",),
        idempotent=True, timeout_seconds=5,
    ),
]
