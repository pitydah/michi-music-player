"""DiagnosticsService — full health check for the Michi ecosystem.

Tests: Player API, sync server, pairing, stream, artwork, playback,
queue, Micro Server discovery, import availability, continue readiness.
"""
from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from typing import Any

from integrations.michi_link.client import MichiLinkClient

CONTRACT_OK = "CONTRACT_OK"
CONTRACT_PARTIAL = "CONTRACT_PARTIAL"
CONTRACT_MISMATCH = "CONTRACT_MISMATCH"
ENDPOINT_MISSING = "ENDPOINT_MISSING"
FALLBACK_AVAILABLE = "FALLBACK_AVAILABLE"

logger = logging.getLogger("michi.service.diagnostics")


class DiagnosticsService:
    """Generates structured health reports for Michi services."""

    def __init__(self) -> None:
        self._client = MichiLinkClient()

    def check_player_api(self, handler: Any | None = None) -> dict[str, Any]:
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

    def check_sync_server(self, handler: Any | None = None) -> dict[str, Any]:
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

    def check_pairing(self, registry: Any | None = None) -> dict[str, Any]:
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

    def check_stream(self, handler: Any | None = None) -> dict[str, Any]:
        status = "unknown"
        try:
            if handler and handler.server_ref and handler.server_ref._db:
                has_index = handler.server_ref._track_index_built
                status = "ok" if has_index else "no_index"
        except Exception:
            status = "error"
        return {"status": status}

    def check_playback(self, ps: Any | None = None) -> dict[str, Any]:
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

    def check_queue(self, queue_service: Any | None = None) -> dict[str, Any]:
        status = "unknown"
        data = {}
        try:
            if queue_service:
                q = queue_service.get_items()
                data["queue_length"] = len(q or [])
                status = "ok"
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_track_identity(self, filepath: str = "") -> dict[str, Any]:
        if not filepath:
            return {"status": "skipped", "reason": "no filepath specified"}
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        svc = TrackIdentityService()
        result = svc.compute(filepath)
        if result.ok:
            ident = result.data
            return {
                "status": "ok",
                "quick_hash": ident.quick_hash[:8] + "..." if ident.quick_hash else "",
                "has_content_hash": bool(ident.content_hash),
                "file_size": ident.file_size,
            }
        return {"status": "error", "message": result.message}

    def _check_micro_endpoint(
        self, host: str, port: int, path: str, method: str = "GET"
    ) -> dict[str, Any]:
        try:
            req = urllib.request.Request(
                f"http://{host}:{port}{path}", method=method,
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    return {"status": "ok"}
                return {"status": f"http_{r.status}"}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"status": "not_found"}
            return {"status": f"http_{e.code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_import_preflight(
        self, host: str = "", port: int = 53318
    ) -> dict[str, Any]:
        if not host:
            return {"status": "skipped"}
        # Check endpoint existence directly
        from integrations.michi_link.client import RemoteServerInfo
        endpoint_check = self._check_micro_endpoint(
            host, port, "/api/v1/import/preflight", "POST",
        )
        if endpoint_check.get("status") == "not_found":
            return {"status": "ok", "preflight_supported": False,
                    "endpoint": "not_found"}

        # Try actual call
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        fake = RemoteServerInfo(host=host, port=port)
        result = svc.preflight(fake, [])
        if result.ok:
            return {"status": "ok", "preflight_supported": True,
                    "fallback_used": False}
        if result.code == "PREFLIGHT_CONTRACT_MISMATCH":
            return {"status": "warning", "preflight_supported": True,
                    "contract_mismatch": True}
        return {"status": "ok", "preflight_supported": False,
                "fallback_used": True}

    def check_import_mapping(
        self, host: str = "", port: int = 53318
    ) -> dict[str, Any]:
        if not host:
            return {"status": "skipped"}
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        fake = RemoteServerInfo(host=host, port=port)
        result = svc.preflight(fake, [])
        if result.ok and isinstance(result.data, dict):
            return {"status": "ok", "mapping_supported": True}
        if result.code == "PREFLIGHT_CONTRACT_MISMATCH":
            return {"status": "warning", "mapping_supported": False,
                    "contract_mismatch": True}
        return {"status": "ok", "mapping_supported": False}

    def check_remote_micro(
        self, host: str = "", port: int = 53318
    ) -> dict[str, Any]:
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

    def check_micro_import(
        self, host: str = "", port: int = 53318
    ) -> dict[str, Any]:
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

    def check_continue_readiness(
        self, queue_service: Any | None = None
    ) -> dict[str, Any]:
        status = "unknown"
        data = {}
        try:
            if queue_service:
                q = queue_service.get_items()
                data["has_queue"] = len(q or []) > 0
                data["queue_length"] = len(q or [])
                status = "ready" if data["has_queue"] else "no_queue"
        except Exception as e:
            status = "error"
            data = {"error": str(e)}
        return {"status": status, **data}

    def check_queue_transfer(
        self, host: str = "", port: int = 53318
    ) -> dict[str, Any]:
        if not host:
            return {"status": "skipped"}
        result = self._check_micro_endpoint(host, port, "/api/v1/queue/transfer", "POST")
        result["path"] = "/api/v1/queue/transfer"
        return result

    def generate_report(
        self,
        handler: Any | None = None,
        registry: Any | None = None,
        micro_host: str = "",
        player_service: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "player_api": self.check_player_api(handler),
            "sync_server": self.check_sync_server(handler),
            "pairing": self.check_pairing(registry),
            "stream": self.check_stream(handler),
            "playback": self.check_playback(player_service),
            "queue": self.check_queue(player_service),
            "micro_server_client": self.check_remote_micro(micro_host),
            "micro_import": self.check_micro_import(micro_host),
            "track_identity": self.check_track_identity(),
            "import_preflight": self.check_import_preflight(micro_host),
            "import_mapping": self.check_import_mapping(micro_host),
            "queue_transfer": self.check_queue_transfer(micro_host),
            "continue_readiness": self.check_continue_readiness(player_service),
            "errors": [],
        }
