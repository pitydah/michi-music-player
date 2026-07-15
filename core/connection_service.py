"""ConnectionService — real connection management for Michi Link, Subsonic, and peers.
Wraps integrations/connections/ and integrations/michi_link/."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.connection_service")


class ConnectionService:
    def __init__(self, connection_manager=None, discovery_manager=None,
                 credentials_store=None, michi_link_client=None):
        self._conn_mgr = connection_manager
        self._disc_mgr = discovery_manager
        self._creds = credentials_store
        self._michi_link = michi_link_client

    @property
    def available(self) -> bool:
        return self._conn_mgr is not None

    def discover(self, timeout_s: float = 5.0) -> list[dict]:
        if self._disc_mgr:
            try:
                return self._disc_mgr.discover(timeout=timeout_s)
            except Exception as e:
                logger.error("Discovery error: %s", e)
        return []

    def connect(self, server_id: str, credentials: dict | None = None) -> dict:
        if self._conn_mgr:
            try:
                result = self._conn_mgr.connect(server_id, credentials or {})
                return {"ok": True, "server_id": server_id, "state": result}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def disconnect(self, server_id: str) -> dict:
        if self._conn_mgr:
            try:
                self._conn_mgr.disconnect(server_id)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def get_connections(self) -> list[dict]:
        if self._conn_mgr:
            try:
                return self._conn_mgr.list_connections()
            except Exception:
                pass
        return []

    def diagnose(self, server_id: str) -> dict:
        from integrations.connections.diagnostics import Diagnostics
        if self._conn_mgr:
            try:
                diag = Diagnostics(self._conn_mgr)
                return diag.run(server_id)
            except Exception as e:
                return {"error": str(e)}
        return {"error": "SERVICE_UNAVAILABLE"}

    def health(self) -> dict:
        return {
            "available": self.available,
            "connection_count": len(self.get_connections()),
            "discovery": self._disc_mgr is not None,
        }

    def shutdown(self):
        if self._conn_mgr and hasattr(self._conn_mgr, 'shutdown'):
            self._conn_mgr.shutdown()
