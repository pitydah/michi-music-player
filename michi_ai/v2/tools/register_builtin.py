from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from michi_ai.v2.core.gateways import (
    AudioLabGateway, ConnectionsGateway, DeviceGateway, DiagnosticsGateway,
    HomeAudioGateway, JobGateway, LibraryDoctorGateway, LibraryGateway,
    LyricsGateway, MetadataGateway, MixGateway, NavigationRequestGateway,
    PlaybackGateway, PlaylistGateway, QueueGateway, RadioGateway,
    SettingsGateway,
)
from michi_ai.v2.core.models import ToolDefinition
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


@dataclass
class AssistantGateways:
    playback: PlaybackGateway | None = None
    queue: QueueGateway | None = None
    library: LibraryGateway | None = None
    playlists: PlaylistGateway | None = None
    mix: MixGateway | None = None
    radio: RadioGateway | None = None
    lyrics: LyricsGateway | None = None
    metadata: MetadataGateway | None = None
    audio_lab: AudioLabGateway | None = None
    library_doctor: LibraryDoctorGateway | None = None
    devices: DeviceGateway | None = None
    connections: ConnectionsGateway | None = None
    home_audio: HomeAudioGateway | None = None
    settings: SettingsGateway | None = None
    diagnostics: DiagnosticsGateway | None = None
    navigation: NavigationRequestGateway | None = None
    jobs: JobGateway | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "playback": self.playback,
            "queue": self.queue,
            "library": self.library,
            "playlist": self.playlists,
            "mix": self.mix,
            "radio": self.radio,
            "audio_lab": self.audio_lab,
            "device": self.devices,
            "settings": self.settings,
            "diagnostics": self.diagnostics,
            "navigation": self.navigation,
            "job": self.jobs,
        }


def _handler(name: str, gws: AssistantGateways) -> callable:
    def _make_handler(gateway_attr: str, method_name: str) -> callable:
        def handler(**kwargs: Any) -> dict[str, Any]:
            gw = getattr(gws, gateway_attr, None)
            if gw is None:
                return {"ok": False, "error": f"Gateway '{gateway_attr}' unavailable", "code": "CAPABILITY_UNAVAILABLE"}
            method = getattr(gw, method_name, None)
            if method is None:
                return {"ok": False, "error": f"Method '{method_name}' not found on gateway", "code": "INTERNAL_ERROR"}
            return method(**kwargs)
        handler.__name__ = f"{gateway_attr}_{method_name}"
        return handler
    return _make_handler


def _make_handler(gateway: Any | None, method_name: str, error_message: str = "") -> callable:
    def handler(**kwargs: Any) -> dict[str, Any]:
        if gateway is None:
            return {"ok": False, "error": error_message or "Gateway unavailable", "code": "CAPABILITY_UNAVAILABLE"}
        method = getattr(gateway, method_name, None)
        if method is None:
            return {"ok": False, "error": f"Method '{method_name}' not found", "code": "INTERNAL_ERROR"}
        return method(**kwargs)
    handler.__name__ = f"handler_{method_name}"
    return handler


def register_builtin_tools(
    registry: ToolRegistryV2,
    gateways: AssistantGateways,
    capabilities: CapabilityResolver | None = None,
) -> None:
    from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS

    gw_map: dict[str, tuple[str, str]] = {
        # library
        "search_library": ("library", "search"),
        "get_track_details": ("library", "get_track"),
        "get_album_details": ("library", "get_album"),
        "get_artist_details": ("library", "get_artist"),
        "list_recent_tracks": ("library", "list_recent"),
        "list_unplayed_tracks": ("library", "list_unplayed"),
        "list_favorites": ("library", "list_favorites"),
        "find_metadata_gaps": ("library", "find_metadata_gaps"),
        # playback
        "play_track": ("playback", "play_track"),
        "play_album": ("playback", "play_album"),
        "play_artist": ("playback", "play_artist"),
        "pause": ("playback", "pause"),
        "resume": ("playback", "resume"),
        "stop": ("playback", "stop"),
        "next": ("playback", "next"),
        "previous": ("playback", "previous"),
        "seek": ("playback", "seek"),
        "set_volume": ("playback", "set_volume"),
        "set_repeat": ("playback", "set_repeat"),
        "set_shuffle": ("playback", "set_shuffle"),
        # queue
        "get_queue": ("queue", "get_queue"),
        "add_to_queue": ("queue", "add_to_queue"),
        "play_next": ("queue", "play_next"),
        "replace_queue": ("queue", "replace_queue"),
        "remove_from_queue": ("queue", "remove_from_queue"),
        "clear_queue": ("queue", "clear_queue"),
        "reorder_queue": ("queue", "reorder_queue"),
        # playlist
        "list_playlists": ("playlists", "list_playlists"),
        "get_playlist": ("playlists", "get_playlist"),
        "draft_playlist": ("playlists", "list_playlists"),
        "create_playlist": ("playlists", "create_playlist"),
        "add_to_playlist": ("playlists", "add_to_playlist"),
        "remove_from_playlist": ("playlists", "remove_from_playlist"),
        "reorder_playlist": ("playlists", "reorder_playlist"),
        "delete_playlist": ("playlists", "create_playlist"),
        # audio lab
        "probe_audio": ("audio_lab", "probe_audio"),
        "analyze_audio": ("audio_lab", "analyze_audio"),
        "recommend_conversion_profile": ("audio_lab", "recommend_conversion"),
        "preview_conversion": ("audio_lab", "preview_conversion"),
        "start_conversion": ("audio_lab", "start_conversion"),
        "cancel_conversion": ("audio_lab", "cancel_conversion"),
        "analyze_replaygain": ("audio_lab", "analyze_replaygain"),
        "check_integrity": ("audio_lab", "check_integrity"),
        "compare_audio": ("audio_lab", "compare_audio"),
        # mix
        "create_smart_mix": ("mix", "create_mix"),
        "explain_mix": ("mix", "explain_mix"),
        "save_mix_as_playlist": ("mix", "save_mix_as_playlist"),
        "cancel_mix_generation": ("mix", "cancel_mix"),
        # metadata
        "inspect_metadata": ("library", "get_track"),
        "suggest_metadata_changes": ("library", "find_metadata_gaps"),
        # library doctor
        "scan_library_health": ("diagnostics", "get_diagnostics"),
        "preview_library_repair": ("diagnostics", "get_diagnostics"),
        "apply_library_repair": ("library", "list_recent"),
        "rollback_library_repair": ("library", "list_recent"),
        # devices
        "list_devices": ("devices", "list_devices"),
        "get_device_details": ("devices", "list_devices"),
        "plan_device_sync": ("devices", "plan_sync"),
        "start_device_sync": ("devices", "start_sync"),
        "cancel_device_sync": ("devices", "cancel_sync"),
        "get_sync_status": ("devices", "diagnose_ecosystem"),
        # diagnostics
        "diagnose_ecosystem": ("devices", "diagnose_ecosystem"),
        "diagnose_micro_server": ("devices", "diagnose_server"),
        "diagnose_home_audio": ("devices", "diagnose_home_audio"),
        "diagnose_pairing": ("devices", "diagnose_pairing"),
        # settings
        "get_setting": ("settings", "get_setting"),
        "list_settings": ("settings", "list_settings"),
        "suggest_setting_change": ("settings", "suggest_change"),
        "preview_setting_change": ("settings", "preview_change"),
        "apply_setting_change": ("settings", "apply_change"),
        "restore_setting": ("settings", "suggest_change"),
        # navigation
        "navigate": ("navigation", "request_navigation"),
    }

    _HANDLER_CACHE: dict[str, callable] = {}

    def get_gateway_handler(name: str) -> callable | None:
        if name in _HANDLER_CACHE:
            return _HANDLER_CACHE[name]
        mapping = gw_map.get(name)
        if mapping is None:
            return None
        gw_attr, method = mapping
        gw = getattr(gateways, gw_attr, None)
        _HANDLER_CACHE[name] = _make_handler(gw, method)
        return _HANDLER_CACHE[name]

    registered_names: set[str] = set()

    for defn in BUILTIN_TOOL_DEFINITIONS:
        name = defn.name
        if name in registered_names:
            import logging
            logging.getLogger(__name__).warning("Duplicate tool definition: %s", name)
            continue

        handler = get_gateway_handler(name)
        if handler is not None:
            defn = ToolDefinition(
                name=defn.name, version=defn.version,
                description=defn.description,
                input_schema=defn.input_schema,
                output_schema=defn.output_schema,
                permission=defn.permission,
                capabilities=defn.capabilities,
                requires_confirmation=defn.requires_confirmation,
                destructive=defn.destructive,
                idempotent=defn.idempotent,
                cancellable=defn.cancellable,
                timeout_seconds=defn.timeout_seconds,
                rollback_tool=defn.rollback_tool,
                tags=defn.tags,
                handler=handler,
            )
        registry.register(defn)
        registered_names.add(name)

    if capabilities is not None:
        capabilities.register_from_gateways(gateways.to_dict())
