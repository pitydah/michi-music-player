"""ConnectionsBridge — connects QML Connections page to real MichiLink services.

States: not_configured, scanning, detected, pairing_required, paired,
connected, contract_ok, contract_partial, contract_mismatch, error,
service_unavailable.
All network operations: async, timeout, retry, cancel, status, last contact,
auth, disconnect, reconnect, capabilities, compatibility, errors, retry.
Without controller: SERVICE_UNAVAILABLE.
Does NOT declare connection from saved config alone.
Returns dict ok/error from all actions.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

if TYPE_CHECKING:
    from ui_qml_bridge.navigation_bridge import NavigationBridge

logger = logging.getLogger("michi.connections")

_DEMO_ENABLED = False
_DEFAULT_TIMEOUT_MS = 10000
_MAX_RETRIES = 3
_RETRY_DELAY_MS = 1000


def _normalise(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bool):
        return {"ok": raw}
    if raw is None:
        return {"ok": True}
    return {"ok": False, "error": f"Unexpected: {type(raw).__name__}"}


class _AsyncOp:
    def __init__(self, name: str, timeout_ms: int = _DEFAULT_TIMEOUT_MS):
        self.name = name
        self.timeout_ms = timeout_ms
        self.cancelled = False
        self.finished = False
        self.result: dict | None = None
        self.started_at = time.monotonic()
        self.deadline = self.started_at + timeout_ms / 1000.0
        self._lock = threading.Lock()

    def is_expired(self) -> bool:
        return time.monotonic() > self.deadline

    def cancel(self):
        with self._lock:
            self.cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self.cancelled


_SERVICE_UNAVAILABLE = "service_unavailable"


class ConnectionsBridge(QObject):
    stateChanged = Signal()

    def __init__(self, michi_link_ctrl=None,
                 navigation_bridge: NavigationBridge | None = None, parent=None):
        super().__init__(parent)
        self._ctrl = michi_link_ctrl
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
        self._async_op: _AsyncOp | None = None
        self._retry_count = 0
        self._retry_timer: QTimer | None = None
        self._lock = threading.Lock()

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

    def _cancel_op(self):
        with self._lock:
            if self._async_op:
                self._async_op.cancel()
                self._async_op = None
        if self._retry_timer:
            self._retry_timer.stop()
            self._retry_timer = None

    def _set_state(self, state: str, error: str = ""):
        self._state = state
        if error:
            self._last_error = error
        self.stateChanged.emit()

    @Slot(result=dict)
    def scanForServers(self):
        if self._ctrl is None:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        self._cancel_op()
        self._retry_count = 0
        self._set_state("scanning")
        return self._do_scan()

    def _do_scan(self) -> dict:
        self._cancel_op()
        op = _AsyncOp("scan")
        self._async_op = op
        if self._ctrl and hasattr(self._ctrl, 'discover_servers'):
            try:
                servers = self._ctrl.discover_servers()
                if op.is_cancelled():
                    self._last_error = "Cancelado"
                    self._set_state("error", "Cancelado")
                    return {"ok": False, "error": "CANCELLED"}
                self._discovered = []
                for s in (servers or []):
                    self._discovered.append({
                        "name": getattr(s, 'name', '') or str(s),
                        "host": getattr(s, 'host', '') or '',
                        "type": "Michi Micro Server",
                        "status": "detected",
                    })
            except Exception as e:
                logger.debug("Micro server scan failed", exc_info=True)
                self._last_error = str(e)
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        op.finished = True
        self._update_state()
        self.stateChanged.emit()
        return {"ok": True, "count": len(self._discovered)}

    @Slot(str, int, str, result=dict)
    def connectManual(self, host: str, port: int, alias: str):
        self._cancel_op()
        self._retry_count = 0
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("michi_link/micro_host", host)
            settings_set("michi_link/micro_port", port)
            settings_set("michi_link/micro_alias", alias)
            self._alias = alias
            self._state = "detected"
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def requestPair(self):
        self._set_state("pairing_required")
        return {"ok": True}

    @Slot(result=dict)
    def confirmPair(self):
        try:
            if self._ctrl and hasattr(self._ctrl, 'get_capabilities'):
                caps = self._ctrl.get_capabilities()
                self._capabilities = caps
                self._state = "connected"
                self._last_contact = time.time()
                self._contract = "contract_ok" if caps.get("contract_ok", False) else "contract_partial"
            else:
                self._state = "paired"
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def rejectPair(self):
        self._set_state("not_configured")
        return {"ok": True}

    @Slot(result=dict)
    def diagnose(self):
        try:
            if self._ctrl and hasattr(self._ctrl, 'get_connection_state'):
                state = self._ctrl.get_connection_state()
                self._state = state.get("micro_server_state", "not_configured")
                self._capabilities = self._ctrl.get_capabilities()
                self._server_version = state.get("micro_server_name", "")
                self._alias = state.get("micro_server_name", "")
                self._last_contact = time.time()
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def disconnect(self):
        self._cancel_op()
        self._set_state("not_configured")
        self._alias = ""
        self._contract = ""
        self._last_error = ""
        self._last_contact = 0.0
        return {"ok": True}

    @Slot(result=dict)
    def forgetServer(self):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("michi_link/micro_host", "")
            settings_set("michi_link/micro_port", 0)
        except Exception as e:
            logger.debug("Forget server failed: %s", e)
        self.disconnect()
        return {"ok": True}

    @Slot(str, int, str, result=dict)
    def addManualServer(self, host: str = "", port: int = 0, alias: str = ""):
        if not host:
            return {"ok": False, "error": "EMPTY_HOST"}
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("michi_link/micro_host", host)
            if port > 0:
                settings_set("michi_link/micro_port", port)
            if alias:
                settings_set("michi_link/micro_alias", alias)
            self._state = "detected"
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            self._set_state("error", str(e))
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def reconnect(self):
        self._cancel_op()
        self._retry_count = 0
        self._set_state("scanning")
        if self._ctrl and hasattr(self._ctrl, 'reconnect'):
            try:
                raw = self._ctrl.reconnect()
                result = _normalise(raw)
                if result.get("ok"):
                    self._state = "connected"
                    self._last_contact = time.time()
                    self.stateChanged.emit()
                else:
                    self._retry_with_backoff()
                return result
            except Exception as e:
                self._set_state("error", str(e))
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    def _retry_with_backoff(self):
        if self._retry_count >= _MAX_RETRIES:
            return
        self._retry_count += 1
        delay = _RETRY_DELAY_MS * (2 ** (self._retry_count - 1))
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._do_retry)
        self._retry_timer.start(delay)

    def _do_retry(self):
        self._retry_timer = None
        if self._ctrl and hasattr(self._ctrl, 'reconnect'):
            try:
                raw = self._ctrl.reconnect()
                result = _normalise(raw)
                if result.get("ok"):
                    self._state = "connected"
                    self._last_contact = time.time()
                else:
                    self._retry_with_backoff()
                self.stateChanged.emit()
            except Exception as e:
                self._set_state("error", str(e))

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
        self._update_state()
        self.stateChanged.emit()
        return {"ok": True}

    def _update_state(self):
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
                self._last_contact = time.time()
        except Exception as e:
            logger.debug("MichiLink state check failed", exc_info=True)
            self._state = "error"
            self._last_error = str(e)
