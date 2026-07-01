"""Confirmation policy for Michi AI actions."""

from michi_ai.tools.tool_permissions import permission_requires_confirmation


def requires_confirmation(permission: str) -> bool:
    return permission_requires_confirmation(permission)


ALWAYS_CONFIRM = frozenset({
    "sync_start",
    "sync_stop",
    "pair_micro_server",
    "apply_config_plan",
    "rollback_config_plan",
    "analyze_track_audio",
    "analyze_selected_tracks",
    "create_playlist_from_selection",
    "queue_selection",
    "start_sync",
    "stop_sync",
    "prepare_mobile_sync",
    "prepare_space_saver",
    "prepare_hifi_profile",
    "prepare_home_audio",
})
