"""HomeAudioService — real multi-room and home audio control.
Wraps Snapcast and Home Assistant adapters."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.home_audio")


class HomeAudioService:
    def __init__(self, snapcast_group_manager=None, snapcast_discovery=None,
                 snapserver_manager=None, ha_client=None, local_media_server=None):
        self._group_mgr = snapcast_group_manager
        self._discovery = snapcast_discovery
        self._snapserver = snapserver_manager
        self._ha_client = ha_client
        self._local_media = local_media_server
        self._connected = False
        self._configured_host = ""
        self._latency_ms = 0

    @property
    def available(self) -> bool:
        return self._group_mgr is not None or self._ha_client is not None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def ha_available(self) -> bool:
        return self._ha_client is not None

    @property
    def snapcast_available(self) -> bool:
        return self._group_mgr is not None or self._discovery is not None

    @property
    def latency_ms(self) -> int:
        return self._latency_ms

    def discover_zones(self) -> list[dict]:
        zones = []
        if self._discovery:
            try:
                discover = getattr(self._discovery, "discover", None)
                if discover is not None:
                    discovered = discover() or []
                else:
                    self._discovery.refresh()
                    discovered = self._discovery.clients()
                for zone in discovered:
                    if isinstance(zone, dict):
                        zones.append(zone)
                    else:
                        zones.append({
                            "id": getattr(zone, "id", getattr(zone, "host", "")),
                            "name": getattr(zone, "name", str(zone)),
                            "type": "snapcast",
                        })
            except Exception as e:
                logger.error("Snapcast discovery error: %s", e)
        if self._ha_client:
            try:
                devices = self._ha_client.get_devices() or []
                for d in devices:
                    zones.append({"id": d.get("entity_id"), "name": d.get("name", ""),
                                  "type": "home_assistant", "state": d.get("state", "")})
            except Exception as e:
                logger.error("HA discovery error: %s", e)
        return zones

    def get_groups(self) -> list[dict]:
        if self._group_mgr:
            try:
                getter = getattr(self._group_mgr, "get_groups", None)
                if getter is None:
                    getter = getattr(self._group_mgr, "groups", None)
                return getter() if getter else []
            except Exception:
                pass
        return []

    def create_group(self, name: str, zone_ids: list[str]) -> dict:
        if self._group_mgr:
            try:
                creator = getattr(self._group_mgr, "create_group", None)
                if creator is not None:
                    group = creator(name, zone_ids)
                else:
                    group = self._group_mgr.add_group(name, zone_ids)
                return {"ok": True, "group_id": group}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def delete_group(self, group_id: str) -> dict:
        if self._group_mgr:
            try:
                deleter = getattr(self._group_mgr, "delete_group", None)
                if deleter is not None:
                    deleter(group_id)
                else:
                    self._group_mgr.remove_group(group_id)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def set_volume(self, zone_id: str, volume: float) -> dict:
        volume = max(0.0, min(1.0, float(volume)))
        if self._group_mgr:
            groups = self.get_groups()
            if any(group.get("id") == zone_id for group in groups):
                self._group_mgr.set_volume(zone_id, volume)
                return {"ok": True}
        if self._ha_client:
            try:
                self._ha_client.set_volume(zone_id, volume)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def mute(self, zone_id: str, muted: bool) -> dict:
        if self._ha_client:
            try:
                self._ha_client.mute(zone_id, muted)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def set_mute(self, zone_id: str, muted: bool) -> dict:
        return self.mute(zone_id, muted)

    def get_zones(self) -> list[dict]:
        return self.discover_zones()

    def get_devices(self) -> list[dict]:
        return [zone for zone in self.discover_zones() if zone.get("type") == "home_assistant"]

    def get_streams(self) -> list[dict]:
        return []

    def configure(self, host: str, port: int = 0, access_token: str = "") -> dict:
        if not host or not access_token:
            return {"ok": False, "error": "MISSING_CONFIGURATION"}
        if self._ha_client is None:
            from integrations.home_assistant.client import HomeAssistantClient

            self._ha_client = HomeAssistantClient()
        scheme = "https" if port == 443 else "http"
        base_url = host if "://" in host else f"{scheme}://{host}"
        if port and f":{port}" not in base_url:
            base_url = f"{base_url}:{port}"
        self._ha_client.configure(base_url, access_token)
        self._configured_host = base_url
        self._connected = False
        return {"ok": True, "state": "configured"}

    def test_connection(self) -> dict:
        if self._ha_client is None or not self._configured_host:
            return {"ok": False, "error": "NOT_CONFIGURED"}
        self._ha_client.test_connection()
        return {"ok": True, "state": "connecting"}

    def group(self, zone_ids: str | list[str]) -> dict:
        members = zone_ids.split(",") if isinstance(zone_ids, str) else list(zone_ids)
        members = [member.strip() for member in members if member.strip()]
        if not members:
            return {"ok": False, "error": "EMPTY_ZONES"}
        return self.create_group("Grupo", members)

    def ungroup(self, zone_id: str) -> dict:
        return self.delete_group(zone_id)

    def set_group_name(self, group_id: str, name: str) -> dict:
        if not self._group_mgr:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        self._group_mgr.rename_group(group_id, name)
        return {"ok": True}

    def set_latency(self, _zone_id: str, latency_ms: int) -> dict:
        self._latency_ms = max(0, int(latency_ms))
        return {"ok": True, "latency_ms": self._latency_ms}

    def select_source(self, _source: str) -> dict:
        return {"ok": False, "error": "CAPABILITY_UNAVAILABLE"}

    def assign_stream(self, _stream_id: str) -> dict:
        return {"ok": False, "error": "CAPABILITY_UNAVAILABLE"}

    def server_handoff(self) -> dict:
        return {"ok": False, "error": "CAPABILITY_UNAVAILABLE"}

    def handoff(self) -> dict:
        return self.server_handoff()

    def transfer_playback(self, _from_zone: str, _to_zone: str) -> dict:
        return {"ok": False, "error": "CAPABILITY_UNAVAILABLE"}

    def playback_transfer(self, _zone_id: str) -> dict:
        return {"ok": False, "error": "CAPABILITY_UNAVAILABLE"}

    def health(self) -> dict:
        return {
            "available": self.available,
            "snapcast": self._group_mgr is not None,
            "home_assistant": self._ha_client is not None,
        }

    def shutdown(self):
        pass
