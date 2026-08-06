from __future__ import annotations

from typing import Any

from michi_ai.v2.core.models import Capability, PermissionLevel


class CapabilityResolver:
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, name: str, available: bool = True, degraded: bool = False, reason: str = "", requires_confirmation: bool = False, permission: PermissionLevel = PermissionLevel.READ_ONLY) -> None:
        existing = self._capabilities.get(name)
        if existing is not None:
            # Re-registration (e.g. capability evidence after tool
            # registration) must not clobber the permission/confirmation
            # contract declared by the tool definitions.
            requires_confirmation = existing.requires_confirmation or requires_confirmation
            permission = existing.permission
        self._capabilities[name] = Capability(
            name=name, available=available, degraded=degraded,
            reason=reason, requires_confirmation=requires_confirmation,
            permission=permission,
        )

    def set_available(self, name: str) -> None:
        cap = self._capabilities.get(name)
        if cap:
            self._capabilities[name] = Capability(
                name=name, available=True, degraded=False,
                reason="", requires_confirmation=cap.requires_confirmation,
                permission=cap.permission,
            )

    def set_degraded(self, name: str, reason: str = "degraded") -> None:
        cap = self._capabilities.get(name)
        if cap:
            self._capabilities[name] = Capability(
                name=name, available=True, degraded=True,
                reason=reason, requires_confirmation=cap.requires_confirmation,
                permission=cap.permission,
            )

    def set_unavailable(self, name: str, reason: str = "unavailable") -> None:
        cap = self._capabilities.get(name)
        if cap:
            self._capabilities[name] = Capability(
                name=name, available=False, degraded=False,
                reason=reason, requires_confirmation=cap.requires_confirmation,
                permission=cap.permission,
            )

    def set_confirmation_required(self, name: str, required: bool = True) -> None:
        cap = self._capabilities.get(name)
        if cap:
            self._capabilities[name] = Capability(
                name=name, available=cap.available, degraded=cap.degraded,
                reason=cap.reason, requires_confirmation=required,
                permission=cap.permission,
            )

    def register_from_gateways(self, gateways: dict[str, Any]) -> None:
        """Register capabilities from GATEWAY EVIDENCE, not object existence.

        A capability is available only when a gateway reports it operational
        through ``operational_capabilities()`` (which derives from backing
        service presence). Every capability declared by the builtin tool
        definitions is (re)registered here, so a tool whose gateway is missing
        or unbacked is blocked at execution time.
        """
        all_caps: set[str] = set()
        evidence: dict[str, bool] = {}
        for _gateway_key, gateway in gateways.items():
            if gateway is None:
                continue
            ops: dict[str, bool] = {}
            if hasattr(gateway, "operational_capabilities"):
                try:
                    ops = dict(gateway.operational_capabilities() or {})
                except Exception:
                    ops = {}
            for cap, available in ops.items():
                all_caps.add(cap)
                evidence[cap] = evidence.get(cap, True) and bool(available)

        from michi_ai.v2.tools.tool_definitions import BUILTIN_TOOL_DEFINITIONS
        for defn in BUILTIN_TOOL_DEFINITIONS:
            for cap in defn.capabilities:
                all_caps.add(cap)

        for cap in all_caps:
            available = evidence.get(cap, False)
            self.register(cap, available=available,
                          reason="" if available else f"No gateway provides '{cap}'")

    def resolve(self, needed: str | list[str]) -> dict[str, Capability]:
        needed_list = [needed] if isinstance(needed, str) else needed
        result: dict[str, Capability] = {}
        for name in needed_list:
            cap = self._capabilities.get(name)
            if cap is not None:
                result[name] = cap
            else:
                result[name] = Capability(
                    name=name, available=False,
                    reason=f"Capability '{name}' not registered",
                )
        return result

    def all_available(self, needed: str | list[str]) -> bool:
        caps = self.resolve(needed)
        return all(c.available for c in caps.values())

    def available(self) -> dict[str, Capability]:
        return {k: v for k, v in self._capabilities.items() if v.available}

    def list_all(self) -> dict[str, Capability]:
        return dict(self._capabilities)

    def clear(self) -> None:
        self._capabilities.clear()

    @staticmethod
    def intent_to_capabilities(intent_id: str) -> list[str]:
        mapping: dict[str, list[str]] = {
            "play_track": ["playback.control", "library.read"],
            "play_album": ["playback.control", "library.read"],
            "play_artist": ["playback.control", "library.read"],
            "play_playlist": ["playback.control", "playlist.read"],
            "play_mix": ["playback.control", "mix.generate"],
            "pause": ["playback.control"],
            "resume": ["playback.control"],
            "stop": ["playback.control"],
            "next": ["playback.control"],
            "previous": ["playback.control"],
            "seek": ["playback.control"],
            "set_volume": ["playback.control"],
            "set_repeat": ["playback.control"],
            "set_shuffle": ["playback.control"],
            "get_queue": ["queue.read"],
            "add_to_queue": ["queue.modify"],
            "play_next": ["queue.modify"],
            "replace_queue": ["queue.modify"],
            "remove_from_queue": ["queue.modify"],
            "clear_queue": ["queue.modify"],
            "reorder_queue": ["queue.modify"],
            "search_library": ["library.search"],
            "get_track_details": ["library.read"],
            "get_album_details": ["library.read"],
            "get_artist_details": ["library.read"],
            "list_recent_tracks": ["library.read"],
            "list_unplayed_tracks": ["library.read"],
            "list_favorites": ["library.read", "history.read"],
            "find_metadata_gaps": ["library.read", "metadata.read"],
            "list_playlists": ["playlist.read"],
            "get_playlist": ["playlist.read"],
            "draft_playlist": ["playlist.modify"],
            "create_playlist": ["playlist.modify"],
            "add_to_playlist": ["playlist.modify"],
            "remove_from_playlist": ["playlist.modify"],
            "reorder_playlist": ["playlist.modify"],
            "create_smart_mix": ["mix.generate"],
            "explain_mix": ["mix.generate"],
            "save_mix_as_playlist": ["playlist.modify"],
            "cancel_mix_generation": ["mix.generate"],
            "inspect_metadata": ["metadata.read"],
            "suggest_metadata_changes": ["metadata.read"],
            "scan_library_health": ["library_doctor.scan"],
            "preview_library_repair": ["library_doctor.scan"],
            "apply_library_repair": ["library_doctor.repair"],
            "probe_audio": ["audio_lab.analyze"],
            "analyze_audio": ["audio_lab.analyze"],
            "recommend_conversion_profile": ["audio_lab.analyze"],
            "preview_conversion": ["audio_lab.convert"],
            "start_conversion": ["audio_lab.convert"],
            "cancel_conversion": ["audio_lab.convert"],
            "analyze_replaygain": ["audio_lab.replaygain"],
            "check_integrity": ["audio_lab.analyze"],
            "compare_audio": ["audio_lab.analyze"],
            "diagnose_ecosystem": ["diagnostics.read"],
            "diagnose_micro_server": ["diagnostics.read"],
            "diagnose_home_audio": ["diagnostics.read"],
            "diagnose_pairing": ["diagnostics.read"],
            "list_devices": ["devices.read"],
            "plan_device_sync": ["devices.sync"],
            "start_device_sync": ["devices.sync"],
            "cancel_device_sync": ["devices.sync"],
            "get_setting": ["settings.read"],
            "suggest_setting_change": ["settings.read"],
            "preview_setting_change": ["settings.read"],
            "apply_setting_change": ["settings.modify"],
            "navigate": ["navigation.request"],
            "enqueue": ["queue.modify"],
            "device_sync": ["devices.sync"],
            "settings_navigation": ["navigation.request"],
            "diagnostics_open": ["diagnostics.read"],
            "route_navigation": ["navigation.request"],
            "mix_generate": ["mix.generate"],
            "playlist_create": ["playlist.modify"],
            "audio_analysis": ["audio_lab.analyze"],
            "metadata_preview": ["metadata.read"],
        }
        return mapping.get(intent_id, [])
