"""Ecosystem snapshot section — sync, connections, home audio, remote servers.

Reports real service state when present; missing/optional services yield
``available: False`` per section with a reason (never invented peers).
"""

from __future__ import annotations

from typing import Any


class EcosystemSectionProvider:
    section_key = "ecosystem"

    def build(self, context) -> dict[str, Any]:
        result: dict[str, Any] = {
            "available": True,
            "mobile_sync": {"available": False, "reason": "device_sync_service_missing"},
            "michi_link": {"available": False, "reason": "connection_service_missing"},
            "home_audio": {"available": False, "reason": "home_audio_service_missing"},
            "remote_music": {"configured": False, "servers": 0},
        }
        try:
            result["mobile_sync"] = self._mobile_sync(context)
        except Exception as exc:
            result["mobile_sync"] = {
                "available": False, "reason": "sync_readback_failed", "error": str(exc)[:200],
            }
        try:
            result["michi_link"] = self._michi_link(context)
        except Exception as exc:
            result["michi_link"] = {
                "available": False, "reason": "michi_link_readback_failed", "error": str(exc)[:200],
            }
        try:
            result["remote_music"] = self._remote_music()
        except Exception:
            result["remote_music"] = {"configured": False, "servers": 0}
        return result

    @staticmethod
    def _mobile_sync(context) -> dict[str, Any]:
        sync = context.services.get("device_sync_service")
        if sync is None:
            return {"available": False, "reason": "device_sync_service_missing"}
        peers = []
        if hasattr(sync, "get_all_peers"):
            try:
                peers = sync.get_all_peers() or []
            except Exception:
                peers = []
        syncing = False
        if hasattr(sync, "is_syncing"):
            try:
                syncing = bool(sync.is_syncing())
            except Exception:
                syncing = False
        return {
            "available": True,
            "peers": len(peers),
            "syncing": syncing,
        }

    @staticmethod
    def _michi_link(context) -> dict[str, Any]:
        link = context.services.get("connection_service")
        if link is None:
            return {"available": False, "reason": "connection_service_missing"}
        state = "unknown"
        if hasattr(link, "get_connection_state"):
            try:
                conn = link.get_connection_state() or {}
                state = conn.get("micro_server_state", "unknown")
            except Exception:
                state = "unknown"
        return {"available": True, "state": state}

    @staticmethod
    def _remote_music() -> dict[str, Any]:
        try:
            from streaming.subsonic_client import load_servers
            servers = load_servers()
            return {"configured": bool(servers), "servers": len(servers)}
        except Exception:
            return {"configured": False, "servers": 0}
