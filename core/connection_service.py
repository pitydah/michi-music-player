"""ConnectionService - UI-independent connection and discovery facade."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict

from integrations.connections.connection_profile import ConnectionProfile

logger = logging.getLogger("michi.connection_service")


class ConnectionService:
    """Own connection profiles and expose the contract consumed by QML."""

    def __init__(self, connection_manager=None, discovery_manager=None,
                 credentials_store=None, michi_link_client=None):
        self._conn_mgr = connection_manager
        self._disc_mgr = discovery_manager
        self._creds = credentials_store
        self._michi_link = michi_link_client
        self.state = "not_configured"
        self.alias = ""
        self.contract = ""
        self.last_error = ""
        self.latency_ms = 0
        self.server_version = ""
        self.last_contact = 0.0
        self.capabilities: dict[str, bool] = {}
        self.discovered: list[dict] = []
        self._current_profile_id = ""

    @property
    def available(self) -> bool:
        return self._conn_mgr is not None

    def _profile_to_dict(self, profile) -> dict:
        if isinstance(profile, dict):
            return dict(profile)
        try:
            return asdict(profile)
        except TypeError:
            return {
                "id": getattr(profile, "id", ""),
                "name": getattr(profile, "name", ""),
                "url": getattr(profile, "url", ""),
                "server_type": getattr(profile, "server_type", "unknown"),
            }

    def discover(self, timeout_s: float = 2.0) -> dict:
        if self._disc_mgr is None:
            return {"ok": False, "error": "DISCOVERY_UNAVAILABLE"}
        try:
            servers = list(self._disc_mgr.scan_mdns() or [])
            servers.extend(self._disc_mgr.scan_jellyfin_udp() or [])
            self.discovered = [self._profile_to_dict(server) for server in servers]
            self.state = "detected" if self.discovered else "not_configured"
            return {"ok": True, "count": len(self.discovered), "servers": self.discovered}
        except Exception as exc:
            self.last_error = str(exc)
            self.state = "error"
            logger.warning("Connection discovery failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def connect_manual(self, host: str, port: int, alias: str) -> dict:
        if self._conn_mgr is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        if not host or not port:
            return {"ok": False, "error": "INVALID_ENDPOINT"}
        profile_id = f"manual:{host}:{port}"
        profile = ConnectionProfile(
            id=profile_id,
            name=alias or host,
            server_type="michi-link",
            url=f"http://{host}:{port}",
            last_status="configured",
        )
        current = self._conn_mgr.get(profile_id)
        if current is None:
            self._conn_mgr.add(profile)
        else:
            self._conn_mgr.update(profile)
        self._current_profile_id = profile_id
        self.alias = profile.name
        self.state = "detected"
        self.last_error = ""
        return {"ok": True, "profile": self._profile_to_dict(profile), "state": self.state}

    def connect(self, server_id: str = "", credentials: dict | None = None) -> dict:
        profile_id = server_id or self._current_profile_id
        if not profile_id or self._conn_mgr is None:
            return {"ok": False, "error": "NOT_CONFIGURED"}
        profile = self._conn_mgr.get(profile_id)
        if profile is None:
            return {"ok": False, "error": "PROFILE_NOT_FOUND"}
        if self._michi_link is None:
            self.state = "detected"
            return {"ok": False, "error": "CLIENT_UNAVAILABLE", "state": self.state}
        try:
            result = self._michi_link.connect(profile.url, credentials or {})
            self.state = "connected"
            self.contract = "contract_ok"
            self.last_contact = time.time()
            return {"ok": True, "result": result, "state": self.state}
        except Exception as exc:
            self.state = "error"
            self.last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def disconnect(self, _server_id: str = "") -> dict:
        if self._michi_link and hasattr(self._michi_link, "disconnect"):
            try:
                self._michi_link.disconnect()
            except Exception as exc:
                self.last_error = str(exc)
                return {"ok": False, "error": str(exc)}
        self.state = "not_configured"
        self.latency_ms = 0
        return {"ok": True}

    def forget(self) -> dict:
        if self._current_profile_id and self._conn_mgr:
            self._conn_mgr.remove(self._current_profile_id)
        self._current_profile_id = ""
        self.alias = ""
        self.contract = ""
        return self.disconnect()

    def get_connections(self) -> list[dict]:
        if self._conn_mgr is None:
            return []
        return [self._profile_to_dict(profile) for profile in self._conn_mgr.list_all()]

    def diagnose(self, server_id: str = "") -> dict:
        profile_id = server_id or self._current_profile_id
        return {
            "ok": bool(profile_id),
            "profile_id": profile_id,
            "state": self.state,
            "latency_ms": self.latency_ms,
            "client_available": self._michi_link is not None,
        }

    def authenticate(self) -> dict:
        return self._client_action("authenticate")

    def pair(self) -> dict:
        self.state = "pairing_required"
        return self._client_action("pair", fallback_ok=True)

    def trust(self) -> dict:
        return self._client_action("trust")

    def confirm_pair(self) -> dict:
        result = self._client_action("confirm_pair", fallback_ok=True)
        if result.get("ok"):
            self.state = "connected"
            self.contract = "contract_ok"
        return result

    def reject_pair(self) -> dict:
        self.state = "detected"
        return self._client_action("reject_pair", fallback_ok=True)

    def compatibility(self) -> dict:
        return {"ok": True, "contract": self.contract or "unknown"}

    def latency(self) -> dict:
        return {"ok": True, "latency_ms": self.latency_ms}

    def reconnect(self) -> dict:
        return self.connect()

    def retry(self) -> dict:
        return self.reconnect()

    def cancel(self) -> dict:
        if self._disc_mgr and hasattr(self._disc_mgr, "cancel"):
            self._disc_mgr.cancel()
        return {"ok": True}

    def _client_action(self, method: str, fallback_ok: bool = False) -> dict:
        fn = getattr(self._michi_link, method, None) if self._michi_link else None
        if fn is None:
            return {"ok": fallback_ok, "error": "CLIENT_UNAVAILABLE"}
        try:
            result = fn()
            self.last_contact = time.time()
            return result if isinstance(result, dict) else {"ok": True, "result": result}
        except Exception as exc:
            self.last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def health(self) -> dict:
        return {
            "available": self.available,
            "connection_count": len(self.get_connections()),
            "discovery": self._disc_mgr is not None,
            "client": self._michi_link is not None,
        }

    def shutdown(self):
        if self._michi_link and hasattr(self._michi_link, "shutdown"):
            self._michi_link.shutdown()
