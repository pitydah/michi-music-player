"""DevicesBridge — connects QML Sync/Devices page to real SyncManager.

Returns dict ok/error from all actions. Does not mark serverActive=true
if start() fails.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sync.sync_manager import SyncManager

logger = logging.getLogger("michi.devices")


class DevicesBridge(QObject):
    stateChanged = Signal()

    def __init__(self, sync_manager: SyncManager | None = None, parent=None):
        super().__init__(parent)
        self._sync_mgr = sync_manager
        self._server_active = False
        self._server_port = 53318
        self._peers: list[dict] = []
        self._paired_devices: list[dict] = []

    @Property(bool, notify=stateChanged)
    def serverActive(self):
        return self._server_active

    @Property(int, notify=stateChanged)
    def serverPort(self):
        return self._server_port

    @Property("QVariantList", notify=stateChanged)
    def peers(self):
        return self._peers

    @Property("QVariantList", notify=stateChanged)
    def pairedDevices(self):
        return self._paired_devices

    @Slot(result=dict)
    def startServer(self):
        if not self._sync_mgr:
            return {"ok": False, "error": "NO_SYNC_MANAGER"}
        try:
            if hasattr(self._sync_mgr, 'start'):
                self._sync_mgr.start()
            self._server_active = True
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            logger.debug("SyncManager start failed", exc_info=True)
            self._server_active = False
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def stopServer(self):
        if not self._sync_mgr:
            return {"ok": True}
        try:
            if hasattr(self._sync_mgr, 'stop'):
                self._sync_mgr.stop()
            self._server_active = False
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            logger.debug("SyncManager stop failed", exc_info=True)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def refresh(self):
        peers = []
        paired = []
        if self._sync_mgr:
            try:
                if hasattr(self._sync_mgr, 'get_all_peers'):
                    all_peers = self._sync_mgr.get_all_peers()
                    for p in all_peers:
                        peers.append({
                            "alias": p.get("alias", "") if isinstance(p, dict) else getattr(p, 'alias', '') or str(p),
                            "device": p.get("device", "desktop") if isinstance(p, dict) else getattr(p, 'device', 'desktop'),
                            "ip": p.get("ip", "") if isinstance(p, dict) else getattr(p, 'ip', ''),
                            "port": p.get("port", 0) if isinstance(p, dict) else getattr(p, 'port', 0),
                        })
            except Exception as e:
                logger.debug("Sync peers refresh failed: %s", e)
            try:
                self._server_active = bool(getattr(self._sync_mgr, 'is_active', False))
                if callable(self._server_active):
                    self._server_active = self._sync_mgr.is_active()
            except Exception:
                pass
            try:
                if hasattr(self._sync_mgr, 'get_paired_devices'):
                    all_paired = self._sync_mgr.get_paired_devices()
                    for p in all_paired:
                        paired.append({
                            "alias": p.get("alias", "") if isinstance(p, dict) else getattr(p, 'alias', '') or str(p),
                            "device": p.get("device", "desktop") if isinstance(p, dict) else getattr(p, 'device', 'desktop'),
                        })
            except Exception as e:
                logger.debug("Sync paired devices refresh failed: %s", e)
        self._peers = peers
        self._paired_devices = paired
        self.stateChanged.emit()
        return {"ok": True, "peers": len(peers), "paired": len(paired)}
