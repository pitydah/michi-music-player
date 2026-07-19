"""QML bridge for verified home-audio distribution and zone control."""

from __future__ import annotations

import logging
import time
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

logger = logging.getLogger("michi.home_audio")

_DEFAULT_TIMEOUT_MS = 8000
_MAX_RETRIES = 2
_RETRY_DELAY_MS = 1500


class HomeAudioBridge(QObject):
    stateChanged = Signal()

    def __init__(
        self,
        home_audio_service: Any = None,
        job_service: Any = None,
        action_registry: Any = None,
        navigation_bridge: Any = None,
        page_state_store: Any = None,
        capability_bridge: Any = None,
        accessibility_bridge: Any = None,
        notification_bridge: Any = None,
        parent=None,
    ):
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
        self._distribution_state = "unavailable"
        self._devices: list[dict] = []
        self._zones: list[dict] = []
        self._receivers: list[dict] = []
        self._streams: list[dict] = []
        self._groups: list[dict] = []
        self._sources: list[dict] = []
        self._servers: list[dict] = []
        self._destinations: list[dict] = []
        self._routes: list[dict] = []
        self._last_error = ""
        self._last_contact = 0.0
        self._retry_count = 0
        self._retry_timer: QTimer | None = None
        self._latency_ms = 0
        self._server_handoff_available = False
        self._offline = False

    @Property(bool, constant=True)
    def homeAssistantAvailable(self):
        return self._ha_svc is not None

    @Property(bool, notify=stateChanged)
    def snapcastAvailable(self):
        return bool(self._servers or self._receivers)

    @Property(bool, notify=stateChanged)
    def receiversAvailable(self):
        return bool(self._receivers)

    @Property(bool, constant=True)
    def zonesSupported(self):
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def groupingSupported(self):
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def volumeSupported(self):
        return self._ha_svc is not None

    @Property(bool, notify=stateChanged)
    def serverHandoffAvailable(self):
        return self._server_handoff_available

    @Property(str, notify=stateChanged)
    def homeAssistantState(self):
        return self._ha_state

    @Property(str, notify=stateChanged)
    def snapcastState(self):
        return self._snapcast_state

    @Property(str, notify=stateChanged)
    def distributionState(self):
        return self._distribution_state

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
    def receiverList(self):
        return self._receivers

    @Property("QVariantList", notify=stateChanged)
    def streams(self):
        return self._streams

    @Property("QVariantList", notify=stateChanged)
    def groups(self):
        return self._groups

    @Property("QVariantList", notify=stateChanged)
    def sources(self):
        return self._sources

    @Property("QVariantList", notify=stateChanged)
    def servers(self):
        return self._servers

    @Property("QVariantList", notify=stateChanged)
    def destinations(self):
        return self._destinations

    @Property("QVariantList", notify=stateChanged)
    def routes(self):
        return self._routes

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
        self._retry_timer.start(min(delay, _DEFAULT_TIMEOUT_MS))

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
        if not callable(fn):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            raw = fn(*args, **kwargs)
            self._last_contact = time.time()
            self._offline = False
            if isinstance(raw, dict) and "ok" in raw:
                if not raw.get("ok"):
                    self._last_error = str(raw.get("error", "OPERATION_FAILED"))
                return raw
            if raw is None:
                return {"ok": True, "result": None}
            return {"ok": True, "result": raw}
        except Exception as exc:
            logger.debug("HomeAudio %s failed", method, exc_info=True)
            self._last_error = str(exc)
            self._offline = True
            return {"ok": False, "error": str(exc)}

    def _list_from_service(self, *method_names: str) -> list[dict]:
        if not self._ha_svc:
            return []
        for method_name in method_names:
            fn = getattr(self._ha_svc, method_name, None)
            if not callable(fn):
                continue
            try:
                value = fn()
            except Exception as exc:
                self._last_error = str(exc)
                logger.debug("HomeAudio %s failed", method_name, exc_info=True)
                continue
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _service_defines(self, method_name: str) -> bool:
        if not self._ha_svc:
            return False
        return callable(getattr(type(self._ha_svc), method_name, None))

    def _refresh_models(self):
        self._devices = self._list_from_service("get_devices")
        self._zones = self._list_from_service("get_zones", "discover_zones")
        self._groups = self._list_from_service("get_groups")
        self._streams = self._list_from_service("get_streams")
        self._sources = self._list_from_service("get_sources") or list(self._streams)
        self._servers = self._list_from_service("get_servers")
        self._receivers = self._list_from_service("get_receivers")
        self._destinations = self._list_from_service("get_destinations")
        self._routes = self._list_from_service("list_routes")

        raw_latency = getattr(self._ha_svc, "latency_ms", 0) if self._ha_svc else 0
        try:
            self._latency_ms = int(raw_latency() if callable(raw_latency) else raw_latency)
        except (TypeError, ValueError):
            self._latency_ms = 0

    @Slot(result=dict)
    def refresh(self):
        self._last_error = ""
        self._offline = False
        if not self._ha_svc:
            self._ha_state = "not_configured"
            self._snapcast_state = "concept"
            self._distribution_state = "unavailable"
            self.stateChanged.emit()
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

        self._refresh_models()
        connected_raw = getattr(self._ha_svc, "is_connected", False)
        try:
            connected = connected_raw() if callable(connected_raw) else bool(connected_raw)
        except Exception:
            connected = False

        self._server_handoff_available = bool(
            getattr(self._ha_svc, "server_handoff_available", False)
        )
        server_running = any(server.get("state") == "running" for server in self._servers)
        receiver_online = any(
            receiver.get("connected") or receiver.get("state") == "online"
            for receiver in self._receivers
        )
        if server_running:
            self._snapcast_state = "running"
        elif receiver_online:
            self._snapcast_state = "connected"
        else:
            self._snapcast_state = "concept"

        if connected:
            self._ha_state = "connected"
            self._last_contact = time.time()
        elif self._devices or self._zones:
            self._ha_state = "degraded"
        else:
            self._ha_state = "not_configured"

        if server_running and receiver_online:
            self._distribution_state = "ready"
        elif self._servers or self._sources or self._destinations or self._routes:
            self._distribution_state = "configured"
        else:
            self._distribution_state = "empty"

        self.stateChanged.emit()
        return {
            "ok": connected or bool(
                self._devices
                or self._zones
                or self._sources
                or self._servers
                or self._routes
            ),
            "connected": connected,
            "distribution_state": self._distribution_state,
        }

    @Slot(result=dict)
    def refreshDistribution(self):
        return self.refresh()

    def _mutate_and_refresh(self, method: str, *args):
        result = self._call_svc(method, *args)
        self._refresh_models()
        self.stateChanged.emit()
        return result

    @Slot(str, int, str, result=dict)
    def configureHomeAssistant(self, host: str = "", port: int = 0, token: str = ""):
        return self._call_svc("configure", host=host, port=port, access_token=token)

    @Slot(result=dict)
    def testHomeAssistant(self):
        result = self._call_svc("test_connection")
        if result.get("ok"):
            self.refresh()
        else:
            self._retry_with_backoff("connected")
        return result

    @Slot(result=dict)
    def discoverReceivers(self):
        if not self._service_defines("discover_receivers"):
            return {"ok": False, "error": "UNSUPPORTED"}
        result = self._call_svc("discover_receivers")
        self._refresh_models()
        self.stateChanged.emit()
        return result

    @Slot(str, result=dict)
    def startServer(self, server_id: str = "local_snapserver"):
        return self._mutate_and_refresh("start_server", server_id)

    @Slot(str, result=dict)
    def stopServer(self, server_id: str = "local_snapserver"):
        return self._mutate_and_refresh("stop_server", server_id)

    @Slot(str, str, "QVariantList", result=dict)
    def createRoute(self, name: str, source_id: str, destination_ids):
        ids = [str(item) for item in (destination_ids or []) if str(item)]
        return self._mutate_and_refresh("create_route", name, source_id, ids)

    @Slot(str, result=dict)
    def startRoute(self, route_id: str):
        return self._mutate_and_refresh("start_route", route_id)

    @Slot(str, result=dict)
    def stopRoute(self, route_id: str):
        return self._mutate_and_refresh("stop_route", route_id)

    @Slot(str, result=dict)
    def deleteRoute(self, route_id: str):
        return self._mutate_and_refresh("delete_route", route_id)

    @Slot(str, result=dict)
    def recoverRoute(self, route_id: str):
        return self._mutate_and_refresh("recover_route", route_id)

    @Slot(str, int, result=dict)
    def setReceiverVolume(self, receiver_id: str, volume: int):
        return self._mutate_and_refresh("set_receiver_volume", receiver_id, volume)

    @Slot(str, bool, result=dict)
    def setReceiverMute(self, receiver_id: str, muted: bool):
        return self._mutate_and_refresh("set_receiver_mute", receiver_id, muted)

    @Slot(str, int, result=dict)
    def setReceiverLatency(self, receiver_id: str, latency_ms: int):
        return self._mutate_and_refresh("set_receiver_latency", receiver_id, latency_ms)

    @Slot(result=dict)
    def openDiagnostics(self):
        health = self._call_svc("health")
        self.stateChanged.emit()
        return {
            "ok": True,
            "ha_state": self._ha_state,
            "snapcast_state": self._snapcast_state,
            "distribution_state": self._distribution_state,
            "devices": len(self._devices),
            "zones": len(self._zones),
            "groups": len(self._groups),
            "streams": len(self._streams),
            "receivers": len(self._receivers),
            "routes": len(self._routes),
            "latency_ms": self._latency_ms,
            "offline": self._offline,
            "health": health,
        }

    @Slot(str, float, result=dict)
    def setZoneVolume(self, zone_id: str, volume: float = 0.5):
        return self._mutate_and_refresh("set_volume", zone_id, volume)

    @Slot(str, bool, result=dict)
    def setZoneMute(self, zone_id: str, muted: bool = False):
        return self._mutate_and_refresh("set_mute", zone_id, muted)

    @Slot(str, result=dict)
    def assignStream(self, stream_id: str = ""):
        return self._mutate_and_refresh("assign_stream", stream_id)

    @Slot(result=dict)
    def disconnectHa(self):
        self._cancel_retry()
        self._ha_state = "not_configured"
        self._devices = []
        self._last_contact = 0.0
        self.stateChanged.emit()
        return {"ok": True, "ui_disconnected": True}

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
        return self._mutate_and_refresh("group", zone_ids)

    @Slot(result=dict)
    def recoverFromOffline(self):
        self._offline = False
        result = self.refresh()
        return {"ok": True, "refresh": result}

    @Slot(result=dict)
    def getLatencyReport(self):
        return {"ok": True, "latency_ms": self._latency_ms, "offline": self._offline}

    @Slot(str, result=dict)
    def ungroupZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("ungroup", zone_id)

    @Slot(str, str, result=dict)
    def renameZone(self, zone_id: str = "", new_name: str = ""):
        if not zone_id or not new_name:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._mutate_and_refresh("set_group_name", zone_id, new_name)

    @Slot(str, result=dict)
    def deleteZone(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("delete_group", zone_id)

    @Slot(str, int, result=dict)
    def setLatency(self, zone_id: str = "", latency_ms: int = 0):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("set_latency", zone_id, latency_ms)

    @Slot(str, result=dict)
    def setSource(self, source: str = ""):
        if not source:
            return {"ok": False, "error": "EMPTY_SOURCE"}
        return self._mutate_and_refresh("select_source", source)

    @Property("QVariant", notify=stateChanged)
    def sourceInfo(self):
        return next(
            (source for source in self._sources if source.get("state") == "playing"),
            {},
        )

    @Property("QVariant", notify=stateChanged)
    def syncStatus(self):
        if (
            self._distribution_state == "unavailable"
            and not self._sources
            and not self._servers
            and not self._receivers
            and not self._routes
        ):
            return {}
        return {
            "state": self._distribution_state,
            "latency_ms": self._latency_ms,
            "offline": self._offline,
            "active_routes": len(
                [route for route in self._routes if route.get("state") == "active"]
            ),
        }

    @Slot(str, str, result=dict)
    def transferPlayback(self, from_zone: str = "", to_zone: str = ""):
        if not from_zone or not to_zone:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._mutate_and_refresh("transfer_playback", from_zone, to_zone)

    @Slot(result=dict)
    def handoffToServer(self):
        return self._call_svc("handoff")

    @Slot(str, result=dict)
    def playbackTransfer(self, zone_id: str = ""):
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("playback_transfer", zone_id)
