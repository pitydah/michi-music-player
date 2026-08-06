"""MobileSyncBridge — QML bridge for mobile device pairing and sync.

Thin adapter: delegates to MobileSyncService (pairing, trust, health) and
never fabricates state. Slot names and property shapes are stable for QML.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.mobile_sync_bridge")


class MobileSyncBridge(QObject):
    stateChanged = Signal()

    def __init__(self, mobile_sync_service=None, parent=None):
        super().__init__(parent)
        self._svc = mobile_sync_service
        self._pairing_state = "idle"
        self._code = ""
        self._qr_data_url = ""
        self._session_id = ""
        self._paired_devices: list[dict] = []

    @Property(str, notify=stateChanged)
    def pairingState(self) -> str:
        return self._pairing_state

    @Property(str, notify=stateChanged)
    def pairingCode(self) -> str:
        return self._code

    @Property(str, notify=stateChanged)
    def qrDataUrl(self) -> str:
        return self._qr_data_url

    @Property("QVariantList", notify=stateChanged)
    def pairedDevices(self) -> list:
        if self._svc:
            return [{"id": d.device_id, "name": d.name, "paired_at": d.paired_at,
                     "trusted": d.trusted and not d.revoked,
                     "revoked": d.revoked}
                    for d in self._svc.paired_devices]
        return list(self._paired_devices)

    @Property("QVariantMap", notify=stateChanged)
    def health(self) -> dict:
        """Consume service health as-is; never fabricate fields."""
        if not self._svc:
            return {"available": False, "server_listening": False}
        return self._svc.health()

    @Slot(result=dict)
    def startPairing(self):
        if not self._svc:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        result = self._svc.start_pairing()
        if result.get("ok"):
            self._session_id = result["session_id"]
            self._code = result["code"]
            self._qr_data_url = result.get("qr_data_uri", "")
            self._pairing_state = "waiting"
            self.stateChanged.emit()
        return result

    @Slot(str, result=dict)
    def verifyPairing(self, code: str):
        if not self._svc or not self._session_id:
            return {"ok": False, "error": "NO_ACTIVE_SESSION"}
        result = self._svc.verify_pairing(self._session_id, code)
        if result.get("ok"):
            self._pairing_state = "verified"
            self.stateChanged.emit()
        return result

    @Slot(str, result=dict)
    def unpairDevice(self, device_id: str):
        if not self._svc:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        result = self._svc.unpair(device_id)
        if result.get("ok"):
            self.stateChanged.emit()
        return result

    @Slot(result=dict)
    def cancelPairing(self):
        self._session_id = ""
        self._code = ""
        self._qr_data_url = ""
        self._pairing_state = "idle"
        self.stateChanged.emit()
        return {"ok": True}
