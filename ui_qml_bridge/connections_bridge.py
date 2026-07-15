from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Property, Slot

if TYPE_CHECKING:
    from ui_qml_bridge.navigation_bridge import NavigationBridge

logger = logging.getLogger("michi.connections")

_SERVICE_UNAVAILABLE = "service_unavailable"


def _normalise(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bool):
        return {"ok": raw}
    if raw is None:
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}
    return {"ok": False, "error": f"Unexpected: {type(raw).__name__}"}


def _method_unavailable(name: str = "") -> dict:
    return {"ok": False, "error": "METHOD_UNAVAILABLE", "message": name or "Method not available"}


class ConnectionsBridge(QObject):
    stateChanged = Signal()

    def __init__(self, michi_link_ctrl=None,
                 navigation_bridge: NavigationBridge | None = None,
                 connection_service=None, parent=None):
        super().__init__(parent)
        self._ctrl = michi_link_ctrl
        self._connection_service = connection_service
        self._nav_bridge = navigation_bridge
        self._state = _SERVICE_UNAVAILABLE if michi_link_ctrl is None else "not_configured"
        self._alias = ""
        self._contract = ""
        self._last_error = ""
        self._latency_ms = 0
        self._server_version = ""
        self._last_contact = 0.0
        self._capabilities: dict = {}
        self._discovered: list[dict] = []

    @Property(str, notify=stateChanged)
    def microServerState(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def microServerAlias(self) -> str:
        return self._alias

    @Property(str, notify=stateChanged)
    def microServerContract(self) -> str:
        return self._contract

    @Property(str, notify=stateChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(int, notify=stateChanged)
    def latencyMs(self) -> int:
        return self._latency_ms

    @Property(str, notify=stateChanged)
    def serverVersion(self) -> str:
        return self._server_version

    @Property("QVariantList", notify=stateChanged)
    def discoveredServers(self) -> list[dict]:
        return self._discovered

    @Property("QVariantList", notify=stateChanged)
    def capabilities(self) -> list[dict]:
        caps = self._capabilities
        return [
            {"key": "can_continue_playback", "label": "Continuar reproduccion",
             "enabled": caps.get("can_continue_playback", False)},
            {"key": "can_import", "label": "Importar musica",
             "enabled": caps.get("can_import", False)},
            {"key": "can_send_genre_playlist", "label": "Enviar playlist de genero",
             "enabled": caps.get("can_send_genre_playlist", False)},
            {"key": "can_send_genre_mix", "label": "Enviar mix de genero",
             "enabled": caps.get("can_send_genre_mix", False)},
        ]

    @Property(float, notify=stateChanged)
    def lastContact(self) -> float:
        return self._last_contact

    @Property("QVariantList", notify=stateChanged)
    def externalServers(self) -> list[dict]:
        return []

    @Property(str, notify=stateChanged)
    def protocol(self) -> str:
        return "michi-link"

    @Property(bool, notify=stateChanged)
    def compatible(self) -> bool:
        return self._contract in ("contract_ok", "contract_partial")

    def _set_state(self, state: str, error: str = ""):
        self._state = state
        if error:
            self._last_error = error
        self.stateChanged.emit()

    def _reflect_from_service(self):
        svc = self._connection_service
        if svc is None:
            return
        try:
            self._state = getattr(svc, 'state', self._state)
            self._alias = getattr(svc, 'alias', self._alias)
            self._contract = getattr(svc, 'contract', self._contract)
            self._last_error = getattr(svc, 'last_error', self._last_error)
            self._latency_ms = getattr(svc, 'latency_ms', self._latency_ms)
            self._server_version = getattr(svc, 'server_version', self._server_version)
            self._last_contact = getattr(svc, 'last_contact', self._last_contact)
            self._capabilities = getattr(svc, 'capabilities', self._capabilities)
            self._discovered = getattr(svc, 'discovered', self._discovered)
        except Exception as e:
            logger.debug("reflect_from_service failed: %s", e)

    @Slot(result=dict)
    def discover(self):
        svc = self._connection_service
        if svc is None:
            if self._ctrl is None:
                return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
            return self._do_discover_legacy()
        try:
            result = svc.discover()
            self._reflect_from_service()
            return result
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    def _do_discover_legacy(self) -> dict:
        if not hasattr(self._ctrl, 'discover_servers'):
            return _method_unavailable("discover_servers")
        try:
            servers = self._ctrl.discover_servers()
            self._discovered = []
            for s in (servers or []):
                self._discovered.append({
                    "name": getattr(s, 'name', '') or str(s),
                    "host": getattr(s, 'host', '') or '',
                    "type": "Michi Micro Server",
                    "status": "detected",
                })
            self._set_state("scanning" if self._discovered else "not_configured")
            self.stateChanged.emit()
            return {"ok": True, "count": len(self._discovered)}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(str, int, str, result=dict)
    def connectManual(self, host: str, port: int, alias: str):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.connect_manual(host, port, alias)
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("connectManual")

    @Slot(result=dict)
    def authenticate(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.authenticate()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("authenticate")

    @Slot(result=dict)
    def pair(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.pair()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("pair")

    @Slot(result=dict)
    def trust(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.trust()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("trust")

    @Slot(result=dict)
    def confirmPair(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.confirm_pair()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("confirmPair")

    @Slot(result=dict)
    def rejectPair(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.reject_pair()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("rejectPair")

    @Slot(result=dict)
    def diagnose(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.diagnose()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("diagnose")

    @Slot(result=dict)
    def connect(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.connect()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("connect")

    @Slot(result=dict)
    def disconnect(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.disconnect()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("disconnect")

    @Slot(result=dict)
    def forget(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.forget()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        self.disconnect()
        return {"ok": True}

    @Slot(result=dict)
    def compatibility(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.compatibility()
                self._reflect_from_service()
                return result
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "compatible": self.compatible}

    @Slot(result=dict)
    def latency(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.latency()
                self._reflect_from_service()
                return result
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "latency_ms": self._latency_ms}

    @Slot(result=dict)
    def reconnect(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.reconnect()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        if self._ctrl and hasattr(self._ctrl, 'reconnect'):
            try:
                raw = self._ctrl.reconnect()
                result = _normalise(raw)
                if result.get("ok"):
                    self._state = "connected"
                    self._last_contact = __import__('time').time()
                self.stateChanged.emit()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def retry(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.retry()
                self._reflect_from_service()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return self.reconnect()

    @Slot(result=dict)
    def cancel(self):
        svc = self._connection_service
        if svc is not None:
            try:
                result = svc.cancel()
                self._reflect_from_service()
                return result
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True}

    # ── Legacy slots (kept for backward compat) ──

    @Slot(result=dict)
    def scanForServers(self):
        return self.discover()

    @Slot(str, int, str, result=dict)
    def addManualServer(self, host: str = "", port: int = 0, alias: str = ""):
        if not host:
            return {"ok": False, "error": "EMPTY_HOST"}
        return self.connectManual(host, port, alias)

    @Slot(str, result=dict)
    def requestPair(self):
        return self.pair()

    @Slot(result=dict)
    def forgetServer(self):
        return self.forget()

    @Slot(str, result=dict)
    def openHomeAudio(self, route: str = "home_audio"):
        if self._nav_bridge and hasattr(self._nav_bridge, 'navigate'):
            try:
                self._nav_bridge.navigate(route)
                return {"ok": True}
            except Exception as e:
                logger.debug("Navigation failed: %s", e)
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def refresh(self):
        self._reflect_from_service()
        if not self._connection_service:
            self._state = _SERVICE_UNAVAILABLE
        self.stateChanged.emit()
        return {"ok": False, "error": _SERVICE_UNAVAILABLE}

    def _update_state_legacy(self):
        if not self._ctrl:
            self._state = _SERVICE_UNAVAILABLE
            return
        try:
            caps = self._ctrl.get_capabilities()
            self._capabilities = caps
            state_val = caps.get("micro_server_state", "not_configured")
            if state_val == "not_configured" and caps.get("micro_server_host"):
                state_val = "detected"
            self._state = state_val
            self._alias = caps.get("micro_server_name", "")
            self._contract = "contract_ok" if caps.get("contract_ok", False) else (
                "contract_partial" if self._state == "connected" else "")
            if self._state == "connected":
                self._last_contact = __import__('time').time()
        except Exception as e:
            logger.debug("MichiLink state check failed", exc_info=True)
            self._state = "error"
            self._last_error = str(e)
