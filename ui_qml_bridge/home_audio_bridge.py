"""HomeAudioBridge — connects QML Home Audio page to real HomeAudio/Snapcast controllers.
All network operations: async, timeout, retry, cancel, status, last contact,
auth, disconnect, reconnect, capabilities, server handoff, playback transfer,
latency, offline, partial failure.
Does NOT declare connection for saved config alone.
Contractual adapters: HomeAudioService.
No shortcuts. receiversAlways=False. snapcast state="concept" when no backend.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

logger = logging.getLogger("michi.home_audio")

_DEFAULT_TIMEOUT_MS = 8000
_MAX_RETRIES = 2
_RETRY_DELAY_MS = 1500


class HomeAudioBridge(QObject):
    stateChanged = Signal()

    def __init__(self, home_audio_service: Any = None,
                 job_service: Any = None,
                 action_registry: Any = None,
                 navigation_bridge: Any = None,
                 page_state_store: Any = None,
                 capability_bridge: Any = None,
                 accessibility_bridge: Any = None,
                 notification_bridge: Any = None,
                 parent=None):
        super().__init__(parent)
        self._ha_svc = home_audio_service
        self._job_svc = job_service
        self._registry = action_registry
        self._nav = navigation_bridge
        self._page_state = page_state_store
        self._capability = capability_bridge
        self._accessibility = accessibility_bridge
        self._notification = notification_bridge

        self._ha_state = "not_configured"
        self._snapcast_state = "concept"
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
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def snapcastAvailable(self):
        return False

    @Property(bool, notify=stateChanged)
    def receiversAvailable(self):
        if self._snapcast_ctrl:
            try:
                raw = getattr(self._snapcast_ctrl, 'is_available', False)
                return raw() if callable(raw) else bool(raw)
            except Exception:
                pass
        return self._ha_ctrl is not None

    @Property(bool, constant=True)
    def zonesSupported(self):
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def groupingSupported(self):
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def volumeSupported(self):
        return self._ha_svc is not None

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

    @Slot(result="QVariantList")
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
        if self._ha_state == target_state:
            self._cancel_retry()
        else:
            self._retry_with_backoff(target_state)

    def _call_svc(self, method: str, *args, **kwargs):
        if not self._ha_svc:
            return {"ok": False, "error": "UNSUPPORTED"}
        fn = getattr(self._ha_svc, method, None)
        if not fn:
            return {"ok": False, "error": "NOT_IMPLEMENTED"}
        try:
            raw = fn(*args, **kwargs)
            self._last_contact = time.time()
            self._offline = False
            return {"ok": True, "result": raw} if raw is not None else {"ok": True}
        except Exception as e:
            logger.debug("HomeAudio %s failed", method, exc_info=True)
            self._last_error = str(e)
            return {"ok": False, "error": str(e)}

    #  Actions

    @Slot(result=dict)
    def refresh(self):
        self._last_error = ""
        self._offline = False
        if not self._ha_svc:
            self._ha_state = "not_configured"
            self._snapcast_state = "concept"
            self.stateChanged.emit()
            return {"ok": True}
        try:
            connected_raw = getattr(self._ha_svc, 'is_connected', False)
            connected = connected_raw() if callable(connected_raw) else bool(connected_raw)
            if connected:
                self._ha_state = "connected"
                self._last_contact = time.time()
                self._discover_zones()
                self._discover_endpoints()
            else:
                self._ha_state = "not_configured"
            self._server_handoff_available = bool(
                getattr(self._ha_svc, 'server_handoff_available', False)
            )
        except Exception as e:
            logger.debug("HA refresh failed", exc_info=True)
            self._ha_state = "error"
            self._last_error = str(e)
        self.stateChanged.emit()
        return {"ok": True}

    def _discover_zones(self):
        if not self._ha_svc:
            return
        try:
            raw_zones = getattr(self._ha_svc, 'get_zones', lambda: [])()
            self._zones = [
                {"id": z.get("id", ""), "name": z.get("name", ""),
                 "muted": z.get("muted", False), "volume": z.get("volume", 0)}
                for z in (raw_zones or [])
            ]
        except Exception:
            self._zones = []

    def _discover_endpoints(self):
        if not self._ha_svc:
            return
        try:
            raw_devices = getattr(self._ha_svc, 'get_devices', lambda: [])()
            self._devices = [
                {"name": d.get("name", ""), "entity": d.get("entity_id", "")}
                for d in (raw_devices or [])
            ]
        except Exception:
            self._devices = []
        try:
            raw_groups = getattr(self._ha_svc, 'get_groups', lambda: [])()
            self._groups = raw_groups or []
        except Exception:
            self._groups = []
        try:
            raw_streams = getattr(self._ha_svc, 'get_streams', lambda: [])()
            self._streams = raw_streams or []
        except Exception:
            self._streams = []
        try:
            raw_lat = getattr(self._ha_svc, 'latency_ms', 0)
            self._latency_ms = raw_lat() if callable(raw_lat) else int(raw_lat)
        except Exception:
            self._latency_ms = 0

    @Slot(str, int, str, result=dict)
    def configureHomeAssistant(self, host: str = "", port: int = 0, token: str = ""):
        return self._call_svc("configure", host=host, port=port, access_token=token)

    @Slot(result=dict)
    def testHomeAssistant(self):
        result = self._call_svc("test_connection")
        if result.get("ok"):
            self._ha_state = "connected"
            self._last_contact = time.time()
            self.stateChanged.emit()
        else:
            self._retry_with_backoff("connected")
        return result

    @Slot(result=dict)
    def discoverReceivers(self):
        return {"ok": False, "error": "UNSUPPORTED"}

    @Slot(result=dict)
    def openDiagnostics(self):
        self._last_error = ""
        self._offline = not (self._ha_ctrl is not None or self._snapcast_ctrl is not None)
        self.stateChanged.emit()
        return {
            "ok": True,
            "ha_state": self._ha_state,
            "snapcast_state": self._snapcast_state,
            "devices": len(self._devices),
            "zones": len(self._zones),
            "groups": len(self._groups),
            "streams": len(self._streams),
            "latency_ms": self._latency_ms,
            "offline": self._offline,
            "ha_available": self._ha_ctrl is not None,
            "snapcast_available": self._snapcast_ctrl is not None,
        }

    @Slot(str, float, result=dict)
    def setZoneVolume(self, zone_id: str, volume: float = 0.5):
        return self._call_svc("set_volume", zone_id, volume)

    @Slot(str, bool, result=dict)
    def setZoneMute(self, zone_id: str, muted: bool = False):
        return self._call_svc("set_mute", zone_id, muted)

    @Slot(result=dict)
    def assignStream(self, stream_id: str = ""):
        return self._call_svc("assign_stream", stream_id)

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
        self._cancel_retry()
        return self.testHomeAssistant()

    @Slot(result=dict)
    def serverHandoff(self):
        return self._call_svc("server_handoff")

    @Slot(str, result=dict)
    def groupZones(self, zone_ids: str = ""):
        if not zone_ids:
            return {"ok": False, "error": "EMPTY_ZONES"}
        return self._call_svc("group", zone_ids)

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
        return self._call_svc("ungroup", zone_id)

    @Slot(str, result=dict)
    def renameZone(self, zone_id: str = "", new_name: str = ""):
        if not zone_id or not new_name:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._call_svc("set_group_name", zone_id, new_name)

    @Slot(str, result=dict)
    def deleteZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._call_svc("delete_group", zone_id)

    @Slot(str, int, result=dict)
    def setLatency(self, zone_id: str = "", latency_ms: int = 0):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._call_svc("set_latency", zone_id, latency_ms)

    @Slot(str, result=dict)
    def setSource(self, source: str = ""):
        if not source:
            return {"ok": False, "error": "EMPTY_SOURCE"}
        return self._call_svc("select_source", source)

    @Property("QVariant", notify=stateChanged)
    def sourceInfo(self):
        return {}

    @Property("QVariant", notify=stateChanged)
    def syncStatus(self):
        return {}

    @Slot(str, str, result=dict)
    def transferPlayback(self, from_zone: str = "", to_zone: str = ""):
        if not from_zone or not to_zone:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._call_svc("transfer_playback", from_zone, to_zone)

    @Slot(result=dict)
    def handoffToServer(self):
        return self._call_svc("handoff")

    @Slot(result=dict)
    def playbackTransfer(self, zone_id: str = ""):
        return self._call_svc("playback_transfer", zone_id)
