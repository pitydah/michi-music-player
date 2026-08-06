"""Semantic tool→gateway mapping guards (ADR-006).

Every tool name must map to the (gateway, method) that actually performs the
operation the name promises. The historical bugs guarded here:

- draft_playlist → list_playlists (drafted nothing)
- delete_playlist → create_playlist (created instead of deleting!)
- apply_library_repair / rollback_library_repair → list_recent
- scan_library_health / preview_library_repair → static diagnostics
- restore_setting → suggest_change stub
- get_sync_status → diagnose_ecosystem
- 20 playlist/device tools dead via ``getattr(gateways, "playlist")`` mismatch
"""
from __future__ import annotations

import inspect

from core.assistant_gateways import AssistantGateways
from michi_ai.v2.tools.register_builtin import GW_MAP
from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS

GATEWAY_CLASSES = {
    "playback": "ProductionPlaybackGateway",
    "queue": "ProductionQueueGateway",
    "library": "ProductionLibraryGateway",
    "playlists": "ProductionPlaylistGateway",
    "mix": "ProductionMixGateway",
    "audio_lab": "ProductionAudioLabGateway",
    "devices": "ProductionDeviceGateway",
    "settings": "ProductionSettingsGateway",
    "diagnostics": "ProductionDiagnosticsGateway",
    "navigation": "ProductionNavigationGateway",
    "jobs": "ProductionJobGateway",
    "library_doctor": "ProductionLibraryDoctorGateway",
}

# Classes that live in core.assistant_metadata_gateway (not assistant_gateways).
GATEWAY_MODULES = {
    "metadata": "core.assistant_metadata_gateway",
}

GATEWAY_CLASSES.update({
    "metadata": "ProductionMetadataGateway",
})

REQUIRED_FIXED_MAPPINGS = {
    "draft_playlist": ("playlists", "create_playlist"),
    "delete_playlist": ("playlists", "delete_playlist"),
    "apply_library_repair": ("library_doctor", "repair"),
    "rollback_library_repair": ("library_doctor", "rollback"),
    "inspect_metadata": ("library", "get_track"),
    "suggest_metadata_changes": ("library", "find_metadata_gaps"),
    "scan_library_health": ("library_doctor", "scan"),
    "preview_library_repair": ("library_doctor", "preview_repair"),
    "restore_setting": ("settings", "apply_change"),
    "get_sync_status": ("devices", "get_sync_status"),
    "diagnose_ecosystem": ("devices", "diagnose_ecosystem"),
    "diagnostics_open": ("diagnostics", "open_diagnostics"),
    "list_devices": ("devices", "list_devices"),
    "get_device_details": ("devices", "get_device_details"),
    "playlist_create": ("playlists", "create_playlist"),
    "metadata_preview": ("metadata", "build_proposal"),
}


def _gateway_module(gw_attr: str):
    module_name = GATEWAY_MODULES.get(gw_attr, "core.assistant_gateways")
    import importlib
    return importlib.import_module(module_name)


def test_every_builtin_tool_has_a_semantic_mapping() -> None:
    tools = {d.name for d in BUILTIN_TOOL_DEFINITIONS}
    mapped = set(GW_MAP)
    assert tools == mapped, (
        f"Tool registry and semantic map diverged: "
        f"tools without mapping: {sorted(tools - mapped)}, "
        f"mappings without tool: {sorted(mapped - tools)}"
    )


def test_previously_wrong_mappings_target_correct_operations() -> None:
    for tool, expected in REQUIRED_FIXED_MAPPINGS.items():
        assert GW_MAP[tool] == expected, (
            f"'{tool}' maps to {GW_MAP[tool]} but must map to {expected}"
        )


def test_gateway_attributes_use_plural_names() -> None:
    """The killer bug: singular attrs that do not exist on AssistantGateways."""
    fields = AssistantGateways.__dataclass_fields__
    for tool, (gw_attr, _method) in GW_MAP.items():
        assert gw_attr in fields, (
            f"Tool '{tool}' references gateway attribute '{gw_attr}' "
            f"which does not exist on AssistantGateways"
        )


def test_mapped_methods_exist_on_the_gateway_classes() -> None:
    for tool, (gw_attr, method) in GW_MAP.items():
        class_name = GATEWAY_CLASSES[gw_attr]
        cls = getattr(_gateway_module(gw_attr), class_name, None)
        assert cls is not None, f"Gateway class '{class_name}' not found"
        assert hasattr(cls, method), (
            f"Tool '{tool}' maps to {class_name}.{method} which does not exist"
        )


def test_no_tool_maps_to_list_recent_except_recent_tools() -> None:
    offenders = [
        tool for tool, (_gw, method) in GW_MAP.items()
        if method == "list_recent" and tool != "list_recent_tracks"
    ]
    assert not offenders, (
        f"Tools abusing list_recent: {offenders} — ADR-006 forbids "
        f"apply_library_repair/rollback_library_repair pointing at list_recent"
    )


def test_no_tool_maps_to_static_diagnostics() -> None:
    """scan_library_health / preview_library_repair must reach the doctor,
    never the static diagnostics gateway."""
    for tool, (gw, method) in GW_MAP.items():
        if tool in ("scan_library_health", "preview_library_repair"):
            assert gw == "library_doctor", (
                f"'{tool}' must reach the library doctor, got {gw}.{method}"
            )


def test_playlist_and_device_tools_reach_real_methods() -> None:
    for tool, (gw, method) in GW_MAP.items():
        if gw != "playlists":
            continue
        assert method in ("list_playlists", "get_playlist", "create_playlist",
                          "add_to_playlist", "remove_from_playlist",
                          "reorder_playlist", "delete_playlist"), (
            f"Playlist tool '{tool}' targets non-CRUD method '{method}'"
        )


def test_gateway_handler_methods_are_inspectable() -> None:
    """The mapped methods must be real methods (not dynamic getattr traps)."""
    for tool, (gw_attr, method) in GW_MAP.items():
        cls = getattr(_gateway_module(gw_attr), GATEWAY_CLASSES[gw_attr])
        member = inspect.getattr_static(cls, method)
        assert inspect.isfunction(member) or isinstance(member, (classmethod, staticmethod)), (
            f"'{tool}' → {cls.__name__}.{method} is not a real method"
        )
