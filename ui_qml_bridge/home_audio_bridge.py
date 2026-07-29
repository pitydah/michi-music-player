"""QML bridge for verified home-audio distribution and zone control."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

logger = logging.getLogger("michi.home_audio")

_DEFAULT_TIMEOUT_MS = 8000
_MAX_RETRIES = 2
_RETRY_DELAY_MS = 1500


class HomeAudioBridge(QObject):
    """Expose verified Home Audio operations and snapshots to QML."""

    # Preserve the established camelCase QML meta-object names while keeping
    # Python attributes compliant with the project signal naming convention.
    state_changed = Signal(name="stateChanged")
    operation_finished = Signal("QVariant", name="operationFinished")

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
        worker_manager: Any = None,
        ha_controller: Any = None,
        snapcast_ctrl: Any = None,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the QML bridge with optional application services.

        Args:
            home_audio_service: Home Audio domain service.
            job_service: Optional background job service.
            action_registry: Optional application action registry.
            navigation_bridge: Optional navigation bridge.
            page_state_store: Optional persisted page-state store.
            capability_bridge: Optional capability bridge.
            accessibility_bridge: Optional accessibility bridge.
            notification_bridge: Optional notification bridge.
            worker_manager: Optional worker manager for blocking operations.
            ha_controller: Legacy Home Assistant service alias.
            snapcast_ctrl: Legacy Snapcast service alias.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        self._ha_svc = home_audio_service or ha_controller or snapcast_ctrl
        self._worker_manager = worker_manager

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
        self._offline = False
        self._operation_in_progress = False
        self._current_operation = ""
        self._operation_error = ""
        self._operation_generation = 0
        service_state_changed = getattr(self._ha_svc, "state_changed", None)
        if service_state_changed is not None and hasattr(service_state_changed, "connect"):
            service_state_changed.connect(self._on_service_state_changed)

    def _on_service_state_changed(self, state: dict) -> None:
        entity_id = str(state.get("entity_id", ""))
        if entity_id.startswith("media_player."):
            attributes = state.get("attributes", {}) or {}
            device = {
                "id": entity_id,
                "entity_id": entity_id,
                "name": attributes.get("friendly_name") or entity_id,
                "state": state.get("state", "unknown"),
                "volume": attributes.get("volume_level", 0.0),
                "muted": bool(attributes.get("is_volume_muted", False)),
                "backend": "home_assistant",
            }
            self._devices = [
                item for item in self._devices if item.get("id") != entity_id
            ] + [device]
            zone = {
                "id": entity_id,
                "name": device["name"],
                "members": [entity_id],
                "devices": [entity_id],
                "stream_id": "",
                "active": device["state"] == "playing",
                "volume": device["volume"],
                "muted": device["muted"],
                "state": device["state"],
                "backend": "home_assistant",
                "routeable": False,
                "routable": False,
            }
            self._zones = [
                item
                for item in self._zones
                if item.get("id") != entity_id
            ] + [zone]
        self.state_changed.emit()

    @Property(bool, notify=state_changed)
    def available(self) -> bool:
        """General availability: service exists AND (snapcast reachable OR HA configured)."""
        return (
            self._ha_svc is not None
            and (self._snapcast_state not in ("unavailable", "concept")
                 or self._ha_state not in ("not_configured", "unavailable"))
        )

    @Property(str, notify=state_changed)
    def streamState(self) -> str:
        """Current stream state: inactive, playing, paused, error."""
        if not self._streams:
            return "inactive"
        active = [s for s in self._streams if s.get("active") or s.get("status") == "playing"]
        if active:
            return "playing"
        if any(s.get("status") == "paused" for s in self._streams):
            return "paused"
        if any(s.get("status") == "error" for s in self._streams):
            return "error"
        return "inactive"

    @Property(bool, constant=True)
    def homeAssistantAvailable(self) -> bool:
        return self._ha_svc is not None

    @Property(bool, notify=state_changed)
    def snapcastAvailable(self) -> bool:
        return bool(self._servers or self._receivers)

    @Property(bool, notify=state_changed)
    def receiversAvailable(self) -> bool:
        return bool(self._receivers)

    @Property(bool, constant=True)
    def zonesSupported(self) -> bool:
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def groupingSupported(self) -> bool:
        return self._ha_svc is not None

    @Property(bool, constant=True)
    def volumeSupported(self) -> bool:
        return self._ha_svc is not None

    @Property(str, notify=state_changed)
    def homeAssistantState(self) -> str:
        return self._ha_state

    def _get_ha_websocket_connected(self) -> bool:
        """Whether Home Assistant real-time state updates are active."""
        value = getattr(self._ha_svc, "websocket_connected", False)
        return value if isinstance(value, bool) else False

    # QML property names are camelCase by contract. Declaring Property with a
    # snake_case getter keeps Python methods compliant because PySide6 Property
    # does not provide the explicit name override available to Signal and Slot.
    haWebSocketConnected = Property(
        bool,
        _get_ha_websocket_connected,
        notify=state_changed,
    )

    @Property(str, notify=state_changed)
    def snapcastState(self) -> str:
        return self._snapcast_state

    @Property(str, notify=state_changed)
    def distributionState(self) -> str:
        return self._distribution_state

    @Property("QVariantList", notify=state_changed)
    def devices(self) -> list[dict]:
        return self._devices

    @Property("QVariantList", notify=state_changed)
    def zones(self) -> list[dict]:
        return self._zones

    @Slot(result="QVariantList")
    def receivers(self) -> list[dict]:
        return self._receivers

    @Property("QVariantList", notify=state_changed)
    def receiverList(self) -> list[dict]:
        return self._receivers

    @Property("QVariantList", notify=state_changed)
    def streams(self) -> list[dict]:
        return self._streams

    @Property("QVariantList", notify=state_changed)
    def groups(self) -> list[dict]:
        return self._groups

    @Property("QVariantList", notify=state_changed)
    def sources(self) -> list[dict]:
        return self._sources

    @Property("QVariantList", notify=state_changed)
    def servers(self) -> list[dict]:
        return self._servers

    @Property("QVariantList", notify=state_changed)
    def destinations(self) -> list[dict]:
        return self._destinations

    @Property("QVariantList", notify=state_changed)
    def routes(self) -> list[dict]:
        return self._routes

    @Property(str, notify=state_changed)
    def lastError(self) -> str:
        return self._last_error

    @Property(float, notify=state_changed)
    def lastContact(self) -> float:
        return self._last_contact

    @Property(int, notify=state_changed)
    def latencyMs(self) -> int:
        return self._latency_ms

    @Property(bool, notify=state_changed)
    def offline(self) -> bool:
        return self._offline

    @Property(bool, notify=state_changed)
    def operationInProgress(self) -> bool:
        return self._operation_in_progress

    @Property(str, notify=state_changed)
    def currentOperation(self) -> str:
        return self._current_operation

    @Property(str, notify=state_changed)
    def operationError(self) -> str:
        return self._operation_error

    def _cancel_retry(self) -> None:
        if self._retry_timer:
            self._retry_timer.stop()
            self._retry_timer = None
        self._retry_count = 0

    def _retry_with_backoff(self, target_state: str = "connected") -> None:
        """Schedule a bounded exponential-backoff refresh."""
        if self._retry_count >= _MAX_RETRIES:
            self._cancel_retry()
            return
        self._retry_count += 1
        delay = _RETRY_DELAY_MS * (2 ** (self._retry_count - 1))
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(lambda: self._do_retry_refresh(target_state))
        self._retry_timer.start(min(delay, _DEFAULT_TIMEOUT_MS))

    def _do_retry_refresh(self, target_state: str) -> None:
        self._retry_timer = None
        self.refresh()
        if self._ha_state == target_state:
            self._cancel_retry()
        else:
            self._retry_with_backoff(target_state)

    def _call_svc(self, method: str, *args, **kwargs) -> dict:
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
            if isinstance(raw, bool):
                return {"ok": raw, **({} if raw else {"error": "METHOD_FAILED"})}
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

    def _service_snapshot(self) -> dict:
        """Read all Home Audio models as one coherent bridge snapshot."""
        return {
            "devices": self._list_from_service("get_devices"),
            "zones": self._list_from_service("get_zones", "discover_zones"),
            "groups": self._list_from_service("get_groups"),
            "streams": self._list_from_service("get_streams"),
            "sources": self._list_from_service("get_sources"),
            "servers": self._list_from_service("get_servers"),
            "receivers": self._list_from_service("get_receivers"),
            "destinations": self._list_from_service("get_destinations"),
            "routes": self._list_from_service("list_routes"),
        }

    def _apply_snapshot(self, snapshot: dict) -> None:
        """Replace bridge models and reconcile persisted routes."""
        self._devices = snapshot.get("devices", [])
        self._zones = snapshot.get("zones", [])
        self._groups = snapshot.get("groups", [])
        self._streams = snapshot.get("streams", [])
        self._sources = snapshot.get("sources", []) or list(self._streams)
        self._servers = snapshot.get("servers", [])
        self._receivers = snapshot.get("receivers", [])
        self._destinations = snapshot.get("destinations", [])
        self._routes = self._reconcile_routes(
            snapshot.get("routes", []),
            self._sources,
            self._destinations,
        )

        raw_latency = getattr(self._ha_svc, "latency_ms", 0) if self._ha_svc else 0
        try:
            self._latency_ms = int(raw_latency() if callable(raw_latency) else raw_latency)
        except (TypeError, ValueError):
            self._latency_ms = 0

    @staticmethod
    def _reconcile_routes(
        routes: list[dict],
        sources: list[dict],
        destinations: list[dict],
    ) -> list[dict]:
        source_ids = {str(item.get("id", "")) for item in sources}
        destination_ids = {str(item.get("id", "")) for item in destinations}
        reconciled = []
        for raw_route in routes:
            route = dict(raw_route)
            reasons = []
            if str(route.get("source_id", "")) not in source_ids:
                reasons.append("SOURCE_NOT_FOUND")
            missing_destinations = [
                str(item)
                for item in route.get("destination_ids", [])
                if str(item) not in destination_ids
            ]
            if missing_destinations:
                reasons.append("DESTINATION_NOT_FOUND")
            route["orphaned"] = bool(reasons)
            route["orphan_reasons"] = reasons
            route["missing_destination_ids"] = missing_destinations
            reconciled.append(route)
        return reconciled

    def _refresh_models(self) -> None:
        self._apply_snapshot(self._service_snapshot())

    def _derive_connection_state(self) -> bool:
        """Derive user-facing connection states from the current models."""
        connected_raw = getattr(self._ha_svc, "is_connected", False)
        try:
            connected = connected_raw() if callable(connected_raw) else bool(connected_raw)
        except Exception:
            connected = False
        server_running = any(server.get("state") == "running" for server in self._servers)
        receiver_online = any(
            receiver.get("connected") or receiver.get("state") == "online"
            for receiver in self._receivers
        )
        self._snapcast_state = "running" if server_running else (
            "connected" if receiver_online else "concept"
        )
        if self._last_error:
            self._ha_state = "error"
        elif connected:
            self._ha_state = "connected"
            self._last_contact = time.time()
        elif self._devices or self._zones:
            self._ha_state = "degraded"
        else:
            self._ha_state = "not_configured"
        if server_running and receiver_online:
            self._distribution_state = "active"
        elif self._servers or self._sources or self._destinations or self._routes:
            self._distribution_state = "configured"
        else:
            self._distribution_state = "stopped"
        return connected

    def _dispatch(self, operation: str, method: str | None = None, *args) -> dict:
        """Run a service operation synchronously or through WorkerManager."""
        if not self._ha_svc:
            return {"ok": False, "error": "UNSUPPORTED"}
        if self._operation_in_progress:
            return {"ok": False, "error": "OPERATION_IN_PROGRESS"}
        if method and not callable(getattr(self._ha_svc, method, None)):
            return {"ok": False, "error": "UNSUPPORTED"}
        if self._worker_manager is None:
            result = self._call_svc(method, *args) if method else {"ok": True}
            self._refresh_models()
            self.state_changed.emit()
            return result

        self._operation_generation += 1
        generation = self._operation_generation
        task_id = f"home_audio.{operation}.{generation}"
        self._operation_in_progress = True
        self._current_operation = operation
        self._operation_error = ""
        self.state_changed.emit()

        def run_operation() -> dict:
            result = self._call_svc(method, *args) if method else {"ok": True}
            return {"result": result, "snapshot": self._service_snapshot()}

        def done(payload: dict) -> None:
            if generation != self._operation_generation:
                return
            result = payload.get("result", {"ok": False, "error": "INVALID_RESULT"})
            self._apply_snapshot(payload.get("snapshot", {}))
            self._derive_connection_state()
            self._operation_in_progress = False
            self._current_operation = ""
            self._operation_error = (
                "" if result.get("ok") else str(result.get("error", "OPERATION_FAILED"))
            )
            self.state_changed.emit()
            self.operation_finished.emit(result)

        def failed(code: str, message: str) -> None:
            if generation != self._operation_generation:
                return
            self._operation_in_progress = False
            self._current_operation = ""
            self._operation_error = message or code
            self._last_error = self._operation_error
            self._offline = True
            result = {"ok": False, "error": code, "message": message}
            self.state_changed.emit()
            self.operation_finished.emit(result)

        handle = self._worker_manager.run_task(
            task_id,
            run_operation,
            owner="home_audio",
            on_done=done,
            on_error=failed,
        )
        if getattr(handle, "state", "") == "failed":
            self._operation_in_progress = False
            self._current_operation = ""
            self._operation_error = getattr(handle, "error_code", "WORKER_REJECTED")
            self.state_changed.emit()
            return {"ok": False, "error": self._operation_error}
        return {"ok": True, "accepted": True, "pending": True, "task_id": task_id}

    @Slot(result=dict)
    def refresh(self) -> dict:
        self._last_error = ""
        self._offline = False
        if not self._ha_svc:
            self._ha_state = "not_configured"
            self._snapcast_state = "concept"
            self._distribution_state = "unavailable"
            self.state_changed.emit()
            return {"ok": True, "available": False, "state": "unavailable"}

        if self._worker_manager is not None:
            return self._dispatch("refresh")
        self._refresh_models()
        connected = self._derive_connection_state()

        self.state_changed.emit()
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

    @Slot(result=dict, name="refreshDistribution")
    def refresh_distribution(self) -> dict:
        return self.refresh()

    def _mutate_and_refresh(self, method: str, *args) -> dict:
        return self._dispatch(method, method, *args)

    @Slot(str, int, str, result=dict, name="configureHomeAssistant")
    def configure_home_assistant(
        self, host: str = "", port: int = 0, token: str = ""
    ) -> dict:
        return self.configure_ha(host, port, token)

    @Slot(str, int, str, result=dict, name="configureHa")
    def configure_ha(self, host: str = "", port: int = 0, token: str = "") -> dict:
        """Validate and forward Home Assistant connection settings."""
        if not self._service_defines("configure"):
            return {"ok": False, "error": "UNSUPPORTED"}
        if not host.strip() or not token.strip():
            return {"ok": False, "error": "MISSING_CREDENTIALS"}
        if port < 0 or port > 65535:
            return {"ok": False, "error": "INVALID_PORT"}
        result = self._call_svc(
            "configure",
            host=host.strip(),
            port=port,
            access_token=token,
        )
        if result.get("ok"):
            self._ha_state = "configured"
            self.state_changed.emit()
        return result

    @Slot(result=dict, name="testHomeAssistant")
    def test_home_assistant(self) -> dict:
        return self._dispatch("test_home_assistant", "test_connection")

    @Slot(result=dict, name="discoverReceivers")
    def discover_receivers(self) -> dict:
        if not self._service_defines("discover_receivers"):
            return {"ok": False, "error": "UNSUPPORTED"}
        result = self._call_svc("discover_receivers")
        self._refresh_models()
        self.state_changed.emit()
        if not result.get("ok"):
            return result
        return {"ok": True, "receivers": list(self._receivers)}

    @Slot(str, result=dict, name="startServer")
    def start_server(self, server_id: str = "local_snapserver") -> dict:
        return self._mutate_and_refresh("start_server", server_id)

    @Slot(result=dict, name="startLocalServer")
    def start_local_server(self) -> dict:
        return self.start_server("local_snapserver")

    @Slot(str, result=dict, name="stopServer")
    def stop_server(self, server_id: str = "local_snapserver") -> dict:
        return self._mutate_and_refresh("stop_server", server_id)

    @Slot(result=dict, name="stopLocalServer")
    def stop_local_server(self) -> dict:
        return self.stop_server("local_snapserver")

    @Slot(str, str, "QVariantList", result=dict, name="createRoute")
    def create_route(
        self,
        name: str,
        source_id: str,
        destination_ids: list | tuple | None,
    ) -> dict:
        ids = [str(item) for item in (destination_ids or []) if str(item)]
        if not source_id:
            return {"ok": False, "error": "UNKNOWN_SOURCE"}
        if not ids:
            return {"ok": False, "error": "UNKNOWN_DESTINATION"}
        return self._mutate_and_refresh("create_route", name, source_id, ids)

    @Slot(str, str, str, "QVariantList", result=dict, name="updateRoute")
    @Slot(str, str, str, "QVariantList", str, result=dict, name="updateRoute")
    def update_route(
        self,
        route_id: str,
        name: str,
        source_id: str,
        destination_ids: list | tuple | None,
        mode: str = "atomic",
    ) -> dict:
        ids = [str(item) for item in (destination_ids or []) if str(item)]
        if not route_id:
            return {"ok": False, "error": "UNKNOWN_ROUTE"}
        return self._mutate_and_refresh(
            "update_route", route_id, name, source_id, ids, mode
        )

    @Slot(str, result=dict, name="startRoute")
    @Slot(str, str, result=dict, name="startRoute")
    def start_route(self, route_id: str, mode: str = "atomic") -> dict:
        return self._mutate_and_refresh("start_route", route_id, mode)

    @Slot(str, result=dict, name="stopRoute")
    def stop_route(self, route_id: str) -> dict:
        return self._mutate_and_refresh("stop_route", route_id)

    @Slot(str, result=dict, name="deleteRoute")
    def delete_route(self, route_id: str) -> dict:
        return self._mutate_and_refresh("delete_route", route_id)

    @Slot(str, result=dict, name="recoverRoute")
    def recover_route(self, route_id: str) -> dict:
        return self._mutate_and_refresh("recover_route", route_id)

    @Slot(str, result=dict, name="retryRoute")
    def retry_route(self, route_id: str) -> dict:
        return self.recover_route(route_id)

    @Slot(str, int, result=dict, name="setReceiverVolume")
    def set_receiver_volume(self, receiver_id: str, volume: int) -> dict:
        return self._mutate_and_refresh("set_receiver_volume", receiver_id, volume)

    @Slot(str, bool, result=dict, name="setReceiverMute")
    def set_receiver_mute(self, receiver_id: str, muted: bool) -> dict:
        return self._mutate_and_refresh("set_receiver_mute", receiver_id, muted)

    @Slot(str, int, result=dict, name="setReceiverLatency")
    def set_receiver_latency(self, receiver_id: str, latency_ms: int) -> dict:
        return self._mutate_and_refresh("set_receiver_latency", receiver_id, latency_ms)

    @Slot(str, str, result=dict, name="setReceiverName")
    def set_receiver_name(self, receiver_id: str, name: str) -> dict:
        return self._mutate_and_refresh("set_receiver_name", receiver_id, name)

    @Slot(str, str, result=dict, name="moveReceiver")
    def move_receiver(self, receiver_id: str, group_id: str) -> dict:
        return self._mutate_and_refresh("move_receiver", receiver_id, group_id)

    @Slot(result=dict, name="openDiagnostics")
    def open_diagnostics(self) -> dict:
        """Return a live Snapserver, FIFO, stream, and receiver health report."""
        health = self._call_svc("health")
        health_data = health.get("result", health) if health.get("ok") else {}
        try:
            from integrations.snapcast.fifo_manager import fifo_path

            fifo = Path(fifo_path())
            fifo_exists = fifo.exists()
            fifo_writable = fifo_exists and os.access(fifo, os.W_OK)
            fifo_size = fifo.stat().st_size if fifo_exists else 0
        except OSError as exc:
            fifo_exists = False
            fifo_writable = False
            fifo_size = 0
            self._last_error = str(exc)
        receiver_latencies = [
            {
                "id": receiver.get("id", ""),
                "name": receiver.get("name", receiver.get("id", "")),
                "latency_ms": int(receiver.get("latency_ms", 0) or 0),
            }
            for receiver in self._receivers
            if receiver.get("connected")
        ]
        if self._last_error or health_data.get("last_error"):
            snapserver_state = "error"
        elif health_data.get("snapserver_running") or self._snapcast_state == "running":
            snapserver_state = "running"
        else:
            snapserver_state = "stopped"
        self.state_changed.emit()
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
            "snapserver_state": snapserver_state,
            "fifo_exists": fifo_exists,
            "fifo_writable": fifo_writable,
            "fifo_size": fifo_size,
            "active_streams": [
                stream
                for stream in self._streams
                if stream.get("active")
                or stream.get("state") == "playing"
                or stream.get("status") == "playing"
            ],
            "connected_receivers": [
                receiver for receiver in self._receivers if receiver.get("connected")
            ],
            "receiver_latencies": receiver_latencies,
            "last_error": self._last_error or str(health_data.get("last_error", "")),
            "health": health_data,
        }

    @Slot(result=dict, name="testTone")
    def test_tone(self) -> dict:
        if not self._ha_svc:
            return {"ok": False, "error": "UNSUPPORTED"}
        for method_name in ("test_tone", "play_test_tone"):
            if callable(getattr(self._ha_svc, method_name, None)):
                return self._call_svc(method_name)
        return {"ok": False, "error": "TEST_TONE_UNSUPPORTED"}

    @Slot(str, float, result=dict, name="setZoneVolume")
    def set_zone_volume(self, zone_id: str, volume: float = 0.5) -> dict:
        return self._mutate_and_refresh("set_volume", zone_id, volume)

    @Slot(str, bool, result=dict, name="setZoneMute")
    def set_zone_mute(self, zone_id: str, muted: bool = False) -> dict:
        return self._mutate_and_refresh("set_mute", zone_id, muted)

    @Slot(str, result=dict, name="assignStream")
    def assign_stream(self, stream_id: str = "") -> dict:
        return self._mutate_and_refresh("assign_stream", stream_id)

    @Slot(result=dict, name="disconnectHa")
    def disconnect_ha(self) -> dict:
        self._cancel_retry()
        result = self._call_svc("disconnect_home_assistant")
        self._ha_state = "not_configured"
        self._devices = []
        self._last_contact = 0.0
        self.state_changed.emit()
        return result

    @Slot(str, str, result=dict, name="assignSourceToZone")
    def assign_source_to_zone(self, zone_id: str, source_id: str) -> dict:
        """Assign a Snapcast stream to a zone and verify it by readback."""
        destination = next(
            (
                item
                for item in [*self._groups, *self._zones]
                if str(item.get("id", "")) == zone_id
            ),
            None,
        )
        if destination is None:
            return {
                "ok": False,
                "error": "UNKNOWN_DESTINATION",
                "stream_id": "",
                "verified": False,
            }
        if source_id not in {str(item.get("id", "")) for item in self._sources}:
            return {
                "ok": False,
                "error": "UNKNOWN_SOURCE",
                "stream_id": str(destination.get("stream_id", "")),
                "verified": False,
            }
        result = self._call_svc("assign_source_to_zone", zone_id, source_id)
        if result.get("ok"):
            self.refresh()
        return result

    @Slot(result=dict, name="reconnectHa")
    def reconnect_ha(self) -> dict:
        self._cancel_retry()
        return self.test_home_assistant()

    @Slot(str, "QVariantList", result=dict, name="createGroup")
    def create_group(self, name: str, receiver_ids: list) -> dict:
        """Create a new group with the given receivers."""
        if not self._ha_svc:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        zone_ids = [str(r.get("id", r)) if isinstance(r, dict) else str(r) for r in receiver_ids]
        result = self._call_svc("create_group", name, zone_ids)
        if result.get("ok"):
            self._refresh_models()
        self.state_changed.emit()
        return result

    @Slot(str, str, "QVariantList", result=dict, name="updateGroup")
    def update_group(self, group_id: str, name: str, receiver_ids: list) -> dict:
        """Update an existing group's name and receiver membership."""
        if not self._ha_svc:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        receiver_id_list = [
            str(receiver.get("id", receiver))
            if isinstance(receiver, dict)
            else str(receiver)
            for receiver in receiver_ids
        ]
        receiver_id_list = list(dict.fromkeys(item for item in receiver_id_list if item))
        current = next((g for g in self._groups if g.get("id") == group_id), None)
        if current is None:
            return {"ok": False, "errors": ["GROUP_NOT_FOUND"]}
        result = self._call_svc("update_group", group_id, name, receiver_id_list)
        if result.get("ok"):
            self._refresh_models()
        self.state_changed.emit()
        return result

    @Slot(str, result=dict, name="groupZones")
    def group_zones(self, zone_ids: str = "") -> dict:
        if not zone_ids:
            return {"ok": False, "error": "EMPTY_ZONES"}
        return self._mutate_and_refresh("group", zone_ids)

    @Slot(result=dict, name="recoverFromOffline")
    def recover_from_offline(self) -> dict:
        self._offline = False
        result = self.refresh()
        return {"ok": True, "refresh": result}

    @Slot(result=dict, name="getLatencyReport")
    def get_latency_report(self) -> dict:
        return {"ok": True, "latency_ms": self._latency_ms, "offline": self._offline}

    @Slot(str, result=dict, name="ungroupZone")
    def ungroup_zone(self, zone_id: str = "") -> dict:
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("ungroup", zone_id)

    @Slot(str, str, result=dict, name="renameZone")
    def rename_zone(self, zone_id: str = "", new_name: str = "") -> dict:
        if not zone_id or not new_name:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._mutate_and_refresh("set_group_name", zone_id, new_name)

    @Slot(str, result=dict, name="deleteZone")
    def delete_zone(self, zone_id: str = "") -> dict:
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("delete_group", zone_id)

    @Slot(str, int, result=dict, name="setLatency")
    def set_latency(self, zone_id: str = "", latency_ms: int = 0) -> dict:
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("set_latency", zone_id, latency_ms)

    @Slot(str, result=dict, name="setSource")
    def set_source(self, source: str = "") -> dict:
        if not source:
            return {"ok": False, "error": "EMPTY_SOURCE"}
        return self._mutate_and_refresh("select_source", source)

    @Property("QVariant", notify=state_changed)
    def sourceInfo(self) -> dict:
        return next(
            (source for source in self._sources if source.get("state") == "playing"),
            {},
        )

    @Property("QVariant", notify=state_changed)
    def syncStatus(self) -> dict:
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

    @Slot(str, str, result=dict, name="transferPlayback")
    def transfer_playback(self, from_zone: str = "", to_zone: str = "") -> dict:
        if not from_zone or not to_zone:
            return {"ok": False, "error": "MISSING_ARGS"}
        return self._mutate_and_refresh("transfer_playback", from_zone, to_zone)

    @Slot(str, result=dict, name="playbackTransfer")
    def playback_transfer(self, zone_id: str = "") -> dict:
        if not zone_id:
            return {"ok": False, "error": "EMPTY_ZONE"}
        return self._mutate_and_refresh("playback_transfer", zone_id)


# Python compatibility aliases for the established QML-facing bridge API.
HomeAudioBridge.refreshDistribution = HomeAudioBridge.refresh_distribution
HomeAudioBridge.configureHomeAssistant = HomeAudioBridge.configure_home_assistant
HomeAudioBridge.configureHa = HomeAudioBridge.configure_ha
HomeAudioBridge.testHomeAssistant = HomeAudioBridge.test_home_assistant
HomeAudioBridge.discoverReceivers = HomeAudioBridge.discover_receivers
HomeAudioBridge.startServer = HomeAudioBridge.start_server
HomeAudioBridge.startLocalServer = HomeAudioBridge.start_local_server
HomeAudioBridge.stopServer = HomeAudioBridge.stop_server
HomeAudioBridge.stopLocalServer = HomeAudioBridge.stop_local_server
HomeAudioBridge.createRoute = HomeAudioBridge.create_route
HomeAudioBridge.updateRoute = HomeAudioBridge.update_route
HomeAudioBridge.startRoute = HomeAudioBridge.start_route
HomeAudioBridge.stopRoute = HomeAudioBridge.stop_route
HomeAudioBridge.deleteRoute = HomeAudioBridge.delete_route
HomeAudioBridge.recoverRoute = HomeAudioBridge.recover_route
HomeAudioBridge.retryRoute = HomeAudioBridge.retry_route
HomeAudioBridge.setReceiverVolume = HomeAudioBridge.set_receiver_volume
HomeAudioBridge.setReceiverMute = HomeAudioBridge.set_receiver_mute
HomeAudioBridge.setReceiverLatency = HomeAudioBridge.set_receiver_latency
HomeAudioBridge.setReceiverName = HomeAudioBridge.set_receiver_name
HomeAudioBridge.moveReceiver = HomeAudioBridge.move_receiver
HomeAudioBridge.openDiagnostics = HomeAudioBridge.open_diagnostics
HomeAudioBridge.testTone = HomeAudioBridge.test_tone
HomeAudioBridge.setZoneVolume = HomeAudioBridge.set_zone_volume
HomeAudioBridge.setZoneMute = HomeAudioBridge.set_zone_mute
HomeAudioBridge.assignStream = HomeAudioBridge.assign_stream
HomeAudioBridge.disconnectHa = HomeAudioBridge.disconnect_ha
HomeAudioBridge.assignSourceToZone = HomeAudioBridge.assign_source_to_zone
HomeAudioBridge.reconnectHa = HomeAudioBridge.reconnect_ha
HomeAudioBridge.createGroup = HomeAudioBridge.create_group
HomeAudioBridge.updateGroup = HomeAudioBridge.update_group
HomeAudioBridge.groupZones = HomeAudioBridge.group_zones
HomeAudioBridge.recoverFromOffline = HomeAudioBridge.recover_from_offline
HomeAudioBridge.getLatencyReport = HomeAudioBridge.get_latency_report
HomeAudioBridge.ungroupZone = HomeAudioBridge.ungroup_zone
HomeAudioBridge.renameZone = HomeAudioBridge.rename_zone
HomeAudioBridge.deleteZone = HomeAudioBridge.delete_zone
HomeAudioBridge.setLatency = HomeAudioBridge.set_latency
HomeAudioBridge.setSource = HomeAudioBridge.set_source
HomeAudioBridge.transferPlayback = HomeAudioBridge.transfer_playback
HomeAudioBridge.playbackTransfer = HomeAudioBridge.playback_transfer
