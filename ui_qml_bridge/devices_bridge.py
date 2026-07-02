"""DevicesBridge — connects QML Sync/Devices page to real SyncManager."""

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.devices")


class DevicesBridge(QObject):
    stateChanged = Signal()

    def __init__(self, sync_manager=None, parent=None):
        super().__init__(parent)
        self._sync_mgr = sync_manager
        self._server_active = False
        self._server_port = 53318
        self._peers = []
        self._paired_devices = []

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

    @Slot()
    def startServer(self):
        if self._sync_mgr and hasattr(self._sync_mgr, 'start'):
            try:
                self._sync_mgr.start()
            except Exception:
                logger.debug("SyncManager start failed", exc_info=True)
        self._server_active = True
        self.stateChanged.emit()

    @Slot()
    def stopServer(self):
        if self._sync_mgr and hasattr(self._sync_mgr, 'stop'):
            try:
                self._sync_mgr.stop()
            except Exception:
                logger.debug("SyncManager stop failed", exc_info=True)
        self._server_active = False
        self.stateChanged.emit()

    @Slot()
    def refresh(self):
        if self._sync_mgr:
            peers = []
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
            except Exception:
                logger.debug("Sync peers refresh failed", exc_info=True)
            self._peers = peers
            self._server_active = hasattr(self._sync_mgr, 'is_active') and self._sync_mgr.is_active
        self.stateChanged.emit()
