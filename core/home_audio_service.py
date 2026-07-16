"""HomeAudioService — real multi-room and home audio control.
Wraps Snapcast and Home Assistant adapters."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.home_audio")


class HomeAudioService:
    def __init__(self, snapcast_group_manager=None, snapcast_discovery=None,
                 snapserver_manager=None, ha_client=None, local_media_server=None,
                 event_bus=None):
        self._group_mgr = snapcast_group_manager
        self._event_bus = event_bus
        self._discovery = snapcast_discovery
        self._snapserver = snapserver_manager
        self._ha_client = ha_client
        self._local_media = local_media_server

    @property
    def available(self) -> bool:
        return self._group_mgr is not None or self._ha_client is not None

    def discover_zones(self) -> list[dict]:
        zones = []
        if self._discovery:
            try:
                zones.extend(self._discovery.discover() or [])
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
                return self._group_mgr.get_groups()
            except Exception:
                pass
        return []

    def create_group(self, name: str, zone_ids: list[str]) -> dict:
        if self._group_mgr:
            try:
                group = self._group_mgr.create_group(name, zone_ids)
                return {"ok": True, "group": group}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def delete_group(self, group_id: str) -> dict:
        if self._group_mgr:
            try:
                self._group_mgr.delete_group(group_id)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def set_volume(self, zone_id: str, volume: float) -> dict:
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

    def start(self):
        pass

    def cancel(self):
        pass

    def health(self) -> dict:
        return {
            "available": self.available,
            "snapcast": self._group_mgr is not None,
            "home_assistant": self._ha_client is not None,
        }

    def shutdown(self):
        pass
