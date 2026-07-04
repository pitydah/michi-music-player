"""ConnectionsBridge — connects QML Connections page to real MichiLink services.

States: not_configured, scanning, detected, pairing_required, paired,
connected, contract_ok, contract_partial, contract_mismatch, error.
"""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Property, Slot

if TYPE_CHECKING:
    from ui.controllers.michi_link_controller import MichiLinkController

logger = logging.getLogger("michi.connections")


class ConnectionsBridge(QObject):
    stateChanged = Signal()

    def __init__(self, michi_link_ctrl: MichiLinkController | None = None, navigation_bridge=None, parent=None):
        super().__init__(parent)
        self._ctrl = michi_link_ctrl
        self._nav_bridge = navigation_bridge
        self._state = "not_configured"
        self._alias = ""
        self._contract = ""
        self._last_error = ""
        self._latency_ms = 0
        self._server_version = ""
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

    @Slot()
    def scanForServers(self):
        self._state = "scanning"
        self.stateChanged.emit()
        if self._ctrl and hasattr(self._ctrl, 'discover_servers'):
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
            except Exception as e:
                logger.debug("Micro server scan failed", exc_info=True)
                self._last_error = str(e)
        if not self._discovered and os.environ.get("MICHI_QML_DEMO") == "1":
            self._discovered = [
                {"name": "Michi Micro Server (demo)", "host": "192.168.1.100:8080",
                 "type": "Michi Micro Server", "status": "detected", "is_demo": True}
            ]
        self._update_state()
        self.stateChanged.emit()

    @Slot(str, int, str)
    def connectManual(self, host: str, port: int, alias: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("michi_link/micro_host", host)
            settings_set("michi_link/micro_port", port)
            settings_set("michi_link/micro_alias", alias)
            self._alias = alias
            self._state = "detected"
        except Exception as e:
            self._state = "error"
            self._last_error = str(e)
        self.stateChanged.emit()

    @Slot()
    def requestPair(self):
        self._state = "pairing_required"
        self.stateChanged.emit()

    @Slot()
    def confirmPair(self):
        try:
            if self._ctrl and hasattr(self._ctrl, 'get_capabilities'):
                caps = self._ctrl.get_capabilities()
                self._capabilities = caps
                self._state = "connected"
                self._contract = caps.get("contract_ok", False)
            else:
                self._state = "paired"
        except Exception as e:
            self._state = "error"
            self._last_error = str(e)
        self.stateChanged.emit()

    @Slot()
    def rejectPair(self):
        self._state = "not_configured"
        self.stateChanged.emit()

    @Slot()
    def diagnose(self):
        try:
            if self._ctrl and hasattr(self._ctrl, 'get_connection_state'):
                state = self._ctrl.get_connection_state()
                self._state = state.get("micro_server_state", "not_configured")
                self._capabilities = self._ctrl.get_capabilities()
                self._server_version = state.get("micro_server_name", "")
                self._alias = state.get("micro_server_name", "")
        except Exception:
            self._state = "error"
            self._last_error = "Diagnóstico falló"
        self.stateChanged.emit()

    @Slot()
    def disconnect(self):
        self._state = "not_configured"
        self._alias = ""
        self._contract = ""
        self._last_error = ""
        self.stateChanged.emit()

    @Slot()
    def forgetServer(self):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("michi_link/micro_host", "")
            settings_set("michi_link/micro_port", 0)
        except Exception:
            pass
        self.disconnect()

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
            self._state = "error"
            self._last_error = str(e)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def openHomeAudio(self, route: str = "home_audio"):
        if self._nav_bridge and hasattr(self._nav_bridge, 'navigate'):
            try:
                self._nav_bridge.navigate(route)
                self.stateChanged.emit()
                return {"ok": True}
            except Exception as e:
                logger.debug("Navigation failed: %s", e)
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot()
    def refresh(self):
        self._update_state()
        self.stateChanged.emit()

    def _update_state(self):
        if not self._ctrl:
            self._state = "not_configured"
            return
        try:
            caps = self._ctrl.get_capabilities()
            self._capabilities = caps
            contract_ok = caps.get("contract_ok", False)
            self._state = caps.get("micro_server_state", "not_configured")
            self._alias = caps.get("micro_server_name", "")
            if contract_ok:
                self._contract = "contract_ok"
            elif self._state == "connected" and not contract_ok:
                self._contract = "contract_partial"
        except Exception as e:
            logger.debug("MichiLink state check failed", exc_info=True)
            self._state = "error"
            self._last_error = str(e)
