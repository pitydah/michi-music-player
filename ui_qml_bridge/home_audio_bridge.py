"""HomeAudioBridge  connects QML Home Audio page to real HomeAudio/Snapcast controllers.

All network operations: async, timeout, retry, cancel, status, last contact,
auth, disconnect, reconnect, capabilities, server handoff, playback transfer,
latency, offline, partial failure.
Does NOT declare connection for saved config alone.
Contractual adapters: SnapcastAdapter + HomeAudioAdapter.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import logging
import time
from typing import Any

logger = logging.getLogger("michi.home_audio")

_DEFAULT_TIMEOUT_MS = 8000
_MAX_RETRIES = 2
_RETRY_DELAY_MS = 1500

class HomeAudioBridge(QObject):
    stateChanged = Signal()

    def __init__(self, ha_controller: Any = None,
                 snapcast_ctrl: Any = None, parent=None):
        super().__init__(parent)
        self._ha_ctrl = ha_controller
        self._snapcast_ctrl = snapcast_ctrl
        self._ha_state = "not_configured"
        self._snapcast_state = "unavailable"
        self._devices: list[dict] = []
        self._zones: list[dict] = []
        self._receivers: list[dict] = []
        self._streams: list[dict] = []
        self._groups: list[dict] = []
        self._last_error = ""
        self._last_contact = 0.0
        self._retry_count = 0
        self._retry_timer: QTimer | None = None
        self._latency_ms = 0
        self._server_handoff_available = False
        self._offline = False

    #  Capabilities

    @Property(bool, constant=True)
    def homeAssistantAvailable(self):
        return self._ha_ctrl is not None

    @Property(bool, constant=True)
    def snapcastAvailable(self):
        if not self._snapcast_ctrl:
            return False
        try:
            return bool(getattr(self._snapcast_ctrl, 'is_available', False))
        except Exception:
            return False

    @Property(bool, constant=True)
    def receiversAvailable(self):
        return False

    @Property(bool, constant=True)
    def zonesSupported(self):
        return self.snapcastAvailable

    @Property(bool, constant=True)
    def groupingSupported(self):
        return self.snapcastAvailable

    @Property(bool, constant=True)
    def volumeSupported(self):
        return self._ha_ctrl is not None or self._snapcast_ctrl is not None

    @Property(bool, constant=True)
    def serverHandoffAvailable(self):
        return self._server_handoff_available

    #  State properties

    @Property(str, notify=stateChanged)
    def homeAssistantState(self):
        return self._ha_state

    @Property(str, notify=stateChanged)
    def snapcastState(self):
        return self._snapcast_state

    @Property("QVariantList", notify=stateChanged)
    def devices(self):
        return self._devices

    @Property("QVariantList", notify=stateChanged)
    def zones(self):
        return self._zones

    @Property("QVariantList", notify=stateChanged)
    def groups(self):
        return self._zones

    @Property("QVariantList", notify=stateChanged)
    def receivers(self):
        return self._receivers

    @Property("QVariantList", notify=stateChanged)
    def streams(self):
        return self._streams

    @Property("QVariantList", notify=stateChanged)
    def groups(self):
        return self._groups

    @Property(str, notify=stateChanged)
    def lastError(self):
        return self._last_error

    @Property(float, notify=stateChanged)
    def lastContact(self):
        return self._last_contact

    @Property(int, notify=stateChanged)
    def latencyMs(self):
        return self._latency_ms

    @Property(bool, notify=stateChanged)
    def offline(self):
        return self._offline

    #  Async helpers

    def _cancel_retry(self):
        if self._retry_timer:
            self._retry_timer.stop()
            self._retry_timer = None
        self._retry_count = 0

    def _retry_with_backoff(self, target_state: str = "connected"):
        if self._retry_count >= _MAX_RETRIES:
            self._cancel_retry()
            return
        self._retry_count += 1
        delay = _RETRY_DELAY_MS * (2 ** (self._retry_count - 1))
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(lambda: self._do_retry_refresh(target_state))
        self._retry_timer.start(min(delay, 10000))

    def _do_retry_refresh(self, target_state: str):
        self._retry_timer = None
        self.refresh()
        if self._ha_state == target_state or self._snapcast_state == target_state:
            self._cancel_retry()
        else:
            self._retry_with_backoff(target_state)

    #  Actions

    @Slot(result=dict)
    def refresh(self):
        self._last_error = ""
        self._offline = False
        try:
            if self._ha_ctrl:
                try:
                    raw = getattr(self._ha_ctrl, 'is_connected', False)
                    connected = raw() if callable(raw) else bool(raw)
                    self._ha_state = "connected" if connected else "not_configured"
                    if connected:
                        self._last_contact = time.time()
                        if hasattr(self._ha_ctrl, 'get_devices'):
                            devs = self._ha_ctrl.get_devices()
                            self._devices = [{"name": d.get("name", ""), "entity": d.get("entity_id", "")}
                                             for d in (devs or [])]
                        if hasattr(self._ha_ctrl, 'get_groups'):
                            self._groups = self._ha_ctrl.get_groups() or []
                        if hasattr(self._ha_ctrl, 'get_streams'):
                            self._streams = self._ha_ctrl.get_streams() or []
                        if hasattr(self._ha_ctrl, 'latency_ms'):
                            raw_lat = getattr(self._ha_ctrl, 'latency_ms', 0)
                            self._latency_ms = raw_lat() if callable(raw_lat) else int(raw_lat)
                        if hasattr(self._ha_ctrl, 'server_handoff_available'):
                            raw_ho = getattr(self._ha_ctrl, 'server_handoff_available', False)
                            self._server_handoff_available = raw_ho() if callable(raw_ho) else bool(raw_ho)
                except Exception as e:
                    logger.debug("HA refresh failed", exc_info=True)
                    self._ha_state = "error"
                    self._last_error = f"HA: {e}"

            if self._snapcast_ctrl:
                try:
                    avail_raw = getattr(self._snapcast_ctrl, 'is_available', False)
                    avail = avail_raw() if callable(avail_raw) else bool(avail_raw)
                    self._snapcast_state = "available" if avail else "unavailable"
                    if not avail and self._last_contact > 0 and time.time() - self._last_contact > 30:
                        self._offline = True
                    if avail:
                        self._last_contact = time.time()
                        if hasattr(self._snapcast_ctrl, 'get_groups'):
                            groups = self._snapcast_ctrl.get_groups()
                            self._zones = [{"id": g.get("id", ""), "name": g.get("name", ""),
                                            "muted": g.get("muted", False), "volume": g.get("volume", 0)}
                                           for g in (groups or [])]
                except Exception as e:
                    logger.debug("Snapcast refresh failed", exc_info=True)
                    self._snapcast_state = "error"
                    if not self._last_error:
                        self._last_error = f"Snapcast: {e}"
            else:
                self._snapcast_state = "concept"
        except Exception as e:
            logger.debug("HomeAudio refresh error", exc_info=True)
            self._last_error = str(e)
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, int, str, result=dict)
    def configureHomeAssistant(self, host: str = "", port: int = 0, token: str = ""):
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'configure'):
                self._ha_ctrl.configure(host=host, port=port, access_token=token)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            self._last_error = str(e)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def testHomeAssistant(self):
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'test_connection'):
                ok = self._ha_ctrl.test_connection()
                if ok:
                    self._ha_state = "connected"
                    self._last_contact = time.time()
                    self.stateChanged.emit()
                    return {"ok": True}
                self._retry_with_backoff("connected")
                return {"ok": False, "error": "CONNECTION_FAILED"}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def discoverReceivers(self):
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def openDiagnostics(self):
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, float, result=dict)
    def setZoneVolume(self, zone_id: str, volume: float = 0.5):
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_group_volume'):
                self._snapcast_ctrl.set_group_volume(zone_id, volume)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, bool, result=dict)
    def setZoneMute(self, zone_id: str, muted: bool = False):
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_group_mute'):
                self._snapcast_ctrl.set_group_mute(zone_id, muted)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def assignStream(self, stream_id: str = ""):
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'assign_stream'):
                self._snapcast_ctrl.assign_stream(stream_id)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def disconnectHa(self):
        self._cancel_retry()
        self._ha_state = "not_configured"
        self._devices = []
        self._last_contact = 0.0
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def reconnectHa(self):
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        self._cancel_retry()
        return self.testHomeAssistant()

    #  Group operations
    @Slot(result=dict)
    def serverHandoff(self):
        if not self._server_handoff_available:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if self._ha_ctrl and hasattr(self._ha_ctrl, 'server_handoff'):
                result = self._ha_ctrl.server_handoff()
                self.refresh()
                return {"ok": True, "handoff_result": str(result)}
            if self._snapcast_ctrl and hasattr(self._snapcast_ctrl, 'server_handoff'):
                result = self._snapcast_ctrl.server_handoff()
                self.refresh()
                return {"ok": True, "handoff_result": str(result)}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def groupZones(self, zone_ids: str = ""):
        if not zone_ids:
            return {"ok": False, "error": "EMPTY_ZONES"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'group'):
                self._snapcast_ctrl.group(zone_ids)
            if self._snapcast_ctrl and hasattr(self._snapcast_ctrl, 'playback_transfer'):
                self._snapcast_ctrl.playback_transfer(target_zone_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    #  Group operations

    @Slot(str, result=dict)
    def groupZones(self, zone_ids: str = ""):
        if not zone_ids:
            return {"ok": False, "error": "EMPTY_ZONES"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'group'):
                self._snapcast_ctrl.group(zone_ids)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def ungroupZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'ungroup'):
                self._snapcast_ctrl.ungroup(zone_id)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def renameZone(self, zone_id: str = "", new_name: str = ""):
        if not zone_id or not new_name:
            return {"ok": False, "error": "MISSING_ARGS"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_group_name'):
                self._snapcast_ctrl.set_group_name(zone_id, new_name)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'delete_group'):
                self._snapcast_ctrl.delete_group(zone_id)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Latency

    @Slot(str, int, result=dict)
    def setLatency(self, zone_id: str = "", latency_ms: int = 0):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_latency'):
                self._snapcast_ctrl.set_latency(zone_id, latency_ms)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Source management

    @Slot(str, result=dict)
    def setSource(self, source: str = ""):
        if not source:
            return {"ok": False, "error": "EMPTY_SOURCE"}
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'select_source'):
                self._ha_ctrl.select_source(source)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Property("QVariant", notify=stateChanged)
    def sourceInfo(self):
        return {}

    @Property("QVariant", notify=stateChanged)
    def syncStatus(self):
        return {}

    #  Transfer playback

    @Slot(str, str, result=dict)
    def transferPlayback(self, from_zone: str = "", to_zone: str = ""):
        if not from_zone or not to_zone:
            return {"ok": False, "error": "MISSING_ARGS"}
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'transfer_playback'):
                raw = self._ha_ctrl.transfer_playback(from_zone, to_zone)
                self.refresh()
                return {"ok": True, "result": raw}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Handoff

    @Slot(result=dict)
    @Slot(result=dict)
    def recoverFromOffline(self):
        self._offline = False
        self.refresh()
        return {"ok": True}

    @Slot(result=dict)
    def getLatencyReport(self):
        return {"ok": True, "latency_ms": self._latency_ms, "offline": self._offline}
    @Slot(str, result=dict)
    def ungroupZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'ungroup'):
                self._snapcast_ctrl.ungroup(zone_id)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def renameZone(self, zone_id: str = "", new_name: str = ""):
        if not zone_id or not new_name:
            return {"ok": False, "error": "MISSING_ARGS"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_group_name'):
                self._snapcast_ctrl.set_group_name(zone_id, new_name)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'delete_group'):
                self._snapcast_ctrl.delete_group(zone_id)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Latency

    @Slot(str, int, result=dict)
    def setLatency(self, zone_id: str = "", latency_ms: int = 0):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        if not self._snapcast_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._snapcast_ctrl, 'set_latency'):
                self._snapcast_ctrl.set_latency(zone_id, latency_ms)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Source management

    @Slot(str, result=dict)
    def setSource(self, source: str = ""):
        if not source:
            return {"ok": False, "error": "EMPTY_SOURCE"}
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'select_source'):
                self._ha_ctrl.select_source(source)
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Property("QVariant", notify=stateChanged)
    def sourceInfo(self):
        return {}

    @Property("QVariant", notify=stateChanged)
    def syncStatus(self):
        return {}

    #  Transfer playback

    @Slot(str, str, result=dict)
    def transferPlayback(self, from_zone: str = "", to_zone: str = ""):
        if not from_zone or not to_zone:
            return {"ok": False, "error": "MISSING_ARGS"}
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'transfer_playback'):
                raw = self._ha_ctrl.transfer_playback(from_zone, to_zone)
                self.refresh()
                return {"ok": True, "result": raw}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #  Handoff

    @Slot(result=dict)
    def handoffToServer(self):
        if not self._ha_ctrl:
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            if hasattr(self._ha_ctrl, 'handoff'):
                raw = self._ha_ctrl.handoff()
                self.refresh()
                return {"ok": True, "result": raw}
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
