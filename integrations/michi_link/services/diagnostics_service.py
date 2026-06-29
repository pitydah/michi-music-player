"""DiagnosticsService — full health check for the Michi ecosystem.

Tests: Player API, sync server, pairing, stream, artwork, playback,
queue, Micro Server discovery, import availability, continue readiness.
"""
from __future__ import annotations

import logging
import time

from integrations.michi_link.client import MichiLinkClient

logger = logging.getLogger("michi.service.diagnostics")


class DiagnosticsService:
    """Generates structured health reports for Michi services."""

    def __init__(self):
        self._client = MichiLinkClient()

    def check_player_api(self, handler=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if handler and handler.server_ref:
                srv = handler.server_ref
                has_acct = bool(srv._local_account and srv._local_account.exists())
                status = "ok"
                data = {
                    "service": "michi-music-player",
                    "api_version": "v1",
                    "local_account": has_acct,
                    "running": srv.is_running,
                }
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_sync_server(self, handler=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if handler and handler.server_ref:
                running = handler.server_ref.is_running
                status = "ok" if running else "stopped"
                data = {"running": running}
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_pairing(self, registry=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if registry:
                devices = registry.list_all()
                paired = [d for d in devices if d.token_hash and not d.revoked_at]
                status = "ok"
                data = {
                    "total_devices": len(devices),
                    "paired": len(paired),
                    "revoked": sum(1 for d in devices if d.revoked_at),
                }
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_stream(self, handler=None) -> dict:
        status = "unknown"
        try:
            if handler and handler.server_ref and handler.server_ref._db:
                has_index = handler.server_ref._track_index_built
                status = "ok" if has_index else "no_index"
        except Exception:
            status = "error"
        return {"status": status}

    def check_playback(self, ps=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if ps:
                st = getattr(ps, "state", None)
                data["state"] = st.name.lower() if st else "stopped"
                status = "ok"
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_queue(self, ps=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if ps:
                q = ps.get_queue()
                data["queue_length"] = len(q or [])
                status = "ok"
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_remote_micro(self, host: str = "", port: int = 53318) -> dict:
        if not host:
            return {"status": "skipped", "reason": "no host specified"}
        start = time.time()
        info = self._client.discover(host, port)
        elapsed = time.time() - start
        if info:
            return {
                "status": "ok",
                "alias": info.alias,
                "server_device_id": info.server_device_id,
                "requires_pairing": info.requires_pairing,
                "response_ms": round(elapsed * 1000, 1),
            }
        return {"status": "unreachable", "response_ms": round(elapsed * 1000, 1)}

    def check_micro_import(self, host: str = "", port: int = 53318) -> dict:
        if not host:
            return {"status": "skipped"}
        info = self._client.discover(host, port)
        if info:
            return {
                "status": "ok",
                "requires_pairing": info.requires_pairing,
                "import_available": True,
            }
        return {"status": "unreachable"}

    def check_continue_readiness(self, ps=None) -> dict:
        status = "unknown"
        data = {}
        try:
            if ps:
                q = ps.get_queue()
                data["has_queue"] = len(q or []) > 0
                data["queue_length"] = len(q or [])
                status = "ready" if data["has_queue"] else "no_queue"
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def generate_report(self, handler=None, registry=None,
                        micro_host: str = "",
                        player_service=None) -> dict:
        return {
            "player_api": self.check_player_api(handler),
            "sync_server": self.check_sync_server(handler),
            "pairing": self.check_pairing(registry),
            "stream": self.check_stream(handler),
            "playback": self.check_playback(player_service),
            "queue": self.check_queue(player_service),
            "micro_server_client": self.check_remote_micro(micro_host),
            "micro_import": self.check_micro_import(micro_host),
            "continue_readiness": self.check_continue_readiness(player_service),
            "errors": [],
        }
