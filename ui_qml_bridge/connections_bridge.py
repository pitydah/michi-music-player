from __future__ import annotations

import logging
import time
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

    def __init__(self, connection_service=None,
                 navigation_bridge: NavigationBridge | None = None,
                 parent=None):
        super().__init__(parent)
        self._connection_service = connection_service
        self._nav_bridge = navigation_bridge
        self._state = _SERVICE_UNAVAILABLE if self._connection_service is None else "not_configured"
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
            {"key": "can_continue_playback", "label": "Continuar reproducción",
             "enabled": caps.get("can_continue_playback", False)},
            {"key": "can_import", "label": "Importar música",
             "enabled": caps.get("can_import", False)},
            {"key": "can_send_genre_playlist", "label": "Enviar playlist de género",
             "enabled": caps.get("can_send_genre_playlist", False)},
            {"key": "can_send_genre_mix", "label": "Enviar mix de género",
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

    def _set_connected(self):
        self._state = "connected"
        self._last_contact = time.time()
        self.stateChanged.emit()

    def _reset(self):
        self._state = "not_configured"
        self._alias = ""
        self._contract = ""
        self._last_error = ""
        self._last_contact = 0.0
        self.stateChanged.emit()

    # ── Operations ──

    @Slot(result=dict)
    def discover(self):
        svc = self._connection_service
        if svc is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            raw = svc.discover()
            if isinstance(raw, list):
                self._discovered = raw
            self._state = "detected"
            self.stateChanged.emit()
            return {"ok": True, "servers": self._discovered}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(str, int, str, result=dict)
    def connectManual(self, host: str, port: int, alias: str):
        svc = self._connection_service
        if svc is None:
            return _method_unavailable("connectManual")
        try:
            svc.connect_manual(host, port, alias)
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._state = "detected"
        self._alias = alias
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def authenticate(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.authenticate()
                return _normalise(raw)
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("authenticate")

    @Slot(result=dict)
    def pair(self):
        svc = self._connection_service
        if svc is None:
            return _method_unavailable("pair")
        try:
            svc.pair()
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._state = "pairing_required"
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def trust(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.trust()
                return _normalise(raw)
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return _method_unavailable("trust")

    @Slot(result=dict)
    def confirmPair(self):
        svc = self._connection_service
        if svc is None:
            return _method_unavailable("confirmPair")
        try:
            svc.confirm_pair()
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._set_connected()
        self._contract = "contract_ok"
        if isinstance(getattr(svc, 'capabilities', None), dict):
            self._capabilities = svc.capabilities
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def rejectPair(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.reject_pair()
                self._reset()
                return _normalise(raw)
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        self._reset()
        return {"ok": True}

    @Slot(result=dict)
    def diagnose(self):
        svc = self._connection_service
        if svc is None:
            return _method_unavailable("diagnose")
        try:
            svc.diagnose()
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._state = "connected"
        self._server_version = "Michi Server"
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def connect(self):
        svc = self._connection_service
        if svc is None:
            return {"ok": False, "error": "NO_CONNECTION_SERVICE"}
        try:
            svc.connect()
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._state = "connected"
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def disconnect(self):
        svc = self._connection_service
        if svc is not None:
            try:
                svc.disconnect()
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        self._reset()
        return {"ok": True}

    @Slot(result=dict)
    def forget(self):
        svc = self._connection_service
        if svc is not None:
            try:
                svc.forget()
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        self._reset()
        return {"ok": True}

    @Slot(result=dict)
    def compatibility(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.compatibility()
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "compatible": self.compatible}

    @Slot(result=dict)
    def latency(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.latency()
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True, "latency_ms": self._latency_ms}

    @Slot(result=dict)
    def reconnect(self):
        svc = self._connection_service
        if svc is None:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            svc.reconnect()
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}
        self._state = "connected"
        self._last_contact = time.time()
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def retry(self):
        svc = self._connection_service
        if svc is not None:
            try:
                raw = svc.retry()
                result = _normalise(raw)
                if result.get("ok"):
                    self._set_connected()
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
                raw = svc.cancel()
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": True}

    @Slot(str, result=dict)
    def editServer(self, connection_id: str):
        svc = self._connection_service
        if svc is not None and hasattr(svc, 'edit_server'):
            try:
                raw = svc.edit_server(connection_id)
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return _method_unavailable("editServer")

    @Slot(str, result=dict)
    def deleteServer(self, connection_id: str):
        svc = self._connection_service
        if svc is not None and hasattr(svc, 'delete_server'):
            try:
                raw = svc.delete_server(connection_id)
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if svc is not None and hasattr(svc, 'forget'):
            return self.forget()
        return _method_unavailable("deleteServer")

    @Slot(str, result=dict)
    def testConnection(self, connection_id: str):
        svc = self._connection_service
        if svc is not None and hasattr(svc, 'test_connection'):
            try:
                raw = svc.test_connection(connection_id)
                return _normalise(raw)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if svc is not None and hasattr(svc, 'diagnose'):
            return self.diagnose()
        return _method_unavailable("testConnection")

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
        if not self._connection_service:
            self._state = _SERVICE_UNAVAILABLE
        self.stateChanged.emit()
        return {"ok": True}

    def _update_state_legacy(self):
        self._state = _SERVICE_UNAVAILABLE
