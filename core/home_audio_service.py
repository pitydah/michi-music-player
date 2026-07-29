"""Home-audio distribution domain service.

The service normalises Snapcast, Home Assistant and local zone-management
adapters behind one truthful contract.  A saved route is configuration only;
it becomes active exclusively after the target Snapcast groups are updated and
read back successfully.
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import struct
import subprocess
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, QSettings, Signal

logger = logging.getLogger("michi.home_audio")

_ROUTES_KEY = "home_audio/distribution_routes_v1"
_SELECTED_SOURCE_KEY = "home_audio/selected_source"
_HA_SELECTED_ENTITIES_KEY = "home_audio/ha_selected_entities_v1"
_ROUTE_TRANSACTION_MODES = {"atomic", "best_effort"}


@dataclass
class RouteTransaction:
    """Transaction for multi-destination route operations.

    Atomic transactions restore every snapshotted mutable value when any
    destination fails. Best-effort transactions retain successful changes and
    expose failed destinations through the commit result.
    """

    mode: str = "atomic"
    _snapshots: list[tuple[Any, Any]] = field(default_factory=list)
    _failed: list[dict] = field(default_factory=list)
    _result: dict | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.mode not in _ROUTE_TRANSACTION_MODES:
            raise ValueError(f"Unsupported route transaction mode: {self.mode}")

    def __enter__(self) -> RouteTransaction:
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        if self._result is None:
            self.rollback() if exc is not None else self.commit()
        return False

    def snapshot(self, data: Any) -> Any:
        """Capture a mutable value for a possible in-place rollback."""
        self._snapshots.append((data, deepcopy(data)))
        return data

    def fail(self, failure: dict) -> None:
        """Record one failed destination operation."""
        self._failed.append(deepcopy(failure))

    @staticmethod
    def _restore(target: Any, snapshot: Any) -> None:
        if isinstance(target, dict) and isinstance(snapshot, dict):
            target.clear()
            target.update(deepcopy(snapshot))
            return
        if isinstance(target, list) and isinstance(snapshot, list):
            target[:] = deepcopy(snapshot)
            return
        raise TypeError("RouteTransaction snapshots must be mutable dicts or lists")

    def commit(self) -> dict:
        """Commit successful work or atomically roll it back after failures."""
        if self._result is not None:
            return deepcopy(self._result)
        if self.mode == "atomic" and self._failed:
            return self.rollback()
        self._snapshots.clear()
        self._result = {
            "ok": True,
            "mode": self.mode,
            "degraded": deepcopy(self._failed),
            "rolled_back": False,
        }
        return deepcopy(self._result)

    def rollback(self) -> dict:
        """Restore all snapshots in reverse order."""
        if self._result is not None:
            return deepcopy(self._result)
        for target, snapshot in reversed(self._snapshots):
            self._restore(target, snapshot)
        self._snapshots.clear()
        self._result = {
            "ok": False,
            "mode": self.mode,
            "degraded": deepcopy(self._failed),
            "rolled_back": True,
        }
        return deepcopy(self._result)


class HomeAudioService(QObject):
    """Coordinate Snapcast, Home Assistant, discovery, and persisted routes.

    Server handoff is intentionally not implemented. Home Audio distributes
    local PCM playback through Snapcast instead of transferring playback to a
    separate media server.
    """

    state_changed = Signal(dict)

    def __init__(
        self,
        snapcast_group_manager: Any = None,
        snapcast_discovery: Any = None,
        snapserver_manager: Any = None,
        snapcast_control: Any = None,
        ha_client: Any = None,
        playback_service: Any = None,
        event_bus: Any = None,
        settings: Any = None,
        parent: QObject | None = None,
    ) -> None:
        """Initialize Home Audio adapters and restore persisted routes.

        Args:
            snapcast_group_manager: Optional configured-group manager.
            snapcast_discovery: Optional Snapclient discovery service.
            snapserver_manager: Optional local Snapserver lifecycle manager.
            snapcast_control: Optional Snapcast JSON-RPC client.
            ha_client: Optional Home Assistant client.
            playback_service: Optional playback state provider.
            event_bus: Optional domain event publisher.
            settings: Optional settings implementation.
        """
        super().__init__(parent)
        self._group_mgr = snapcast_group_manager
        self._event_bus = event_bus
        self._discovery = snapcast_discovery
        self._snapserver = snapserver_manager
        self._snapcast = snapcast_control
        self._ha_client = ha_client
        self._playback = playback_service
        self._settings = settings or QSettings("Michi", "MusicPlayer")
        self._routes: list[dict] = []
        self._home_assistant_instances: list[dict] = []
        self._selected_ha_entity_ids = self._load_selected_ha_entity_ids()
        self._selected_source = str(self._settings.value(_SELECTED_SOURCE_KEY, "") or "")
        self._last_error = ""
        self._last_refresh = 0.0
        self._load_routes()
        ha_state_changed = getattr(self._ha_client, "state_changed", None)
        if ha_state_changed is not None and hasattr(ha_state_changed, "connect"):
            ha_state_changed.connect(self._on_home_assistant_state_changed)
        websocket_connection_changed = getattr(
            self._ha_client,
            "websocket_connection_changed",
            None,
        )
        if websocket_connection_changed is not None and hasattr(
            websocket_connection_changed,
            "connect",
        ):
            websocket_connection_changed.connect(
                self._on_home_assistant_connection_changed
            )

    @property
    def available(self) -> bool:
        return any(
            backend is not None
            for backend in (
                self._group_mgr,
                self._discovery,
                self._snapserver,
                self._snapcast,
                self._ha_client,
            )
        )

    @property
    def latency_ms(self) -> int:
        latencies = [
            int(receiver.get("latency_ms", 0) or 0)
            for receiver in self.get_receivers()
            if receiver.get("connected")
        ]
        return max(latencies, default=0)

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def websocket_connected(self) -> bool:
        """Whether Home Assistant has an authenticated WebSocket subscription."""
        value = getattr(self._ha_client, "websocket_connected", False)
        return value if isinstance(value, bool) else False

    def _on_home_assistant_state_changed(self, state: dict) -> None:
        current = dict(state)
        entity_id = str(current.get("entity_id", ""))
        current["imported"] = (
            self._selected_ha_entity_ids is None
            or entity_id in self._selected_ha_entity_ids
        )
        self.state_changed.emit(current)

    def _on_home_assistant_connection_changed(self, connected: bool) -> None:
        self.state_changed.emit(
            {"source": "home_assistant_websocket", "connected": connected}
        )

    def is_connected(self) -> bool:
        snapcast_connected = bool(
            self._snapcast is not None and getattr(self._snapcast, "connected", False)
        )
        ha_connected = bool(
            self._ha_client is not None and getattr(self._ha_client, "connected", False)
        )
        server_running = bool(
            self._snapserver is not None and getattr(self._snapserver, "is_running", False)
        )
        return snapcast_connected or ha_connected or server_running

    def _load_routes(self) -> None:
        raw = self._settings.value(_ROUTES_KEY, "[]")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            self._routes = [route for route in (parsed or []) if isinstance(route, dict)]
            for route in self._routes:
                if route.get("state") in {"active", "degraded", "starting"}:
                    route["state"] = "configured"
                route.setdefault("last_error", route.get("error", ""))
                route.setdefault("destination_errors", {})
        except (TypeError, ValueError):
            logger.warning("Invalid persisted home-audio routes; resetting them")
            self._routes = []

    def _load_selected_ha_entity_ids(self) -> set[str] | None:
        raw = self._settings.value(_HA_SELECTED_ENTITIES_KEY, None)
        if raw is None:
            return None
        try:
            values = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Invalid Home Assistant entity selection; importing all entities")
            return None
        if not isinstance(values, list):
            return None
        return {str(entity_id) for entity_id in values if str(entity_id)}

    def _save_routes(self) -> None:
        self._settings.setValue(_ROUTES_KEY, json.dumps(self._routes, ensure_ascii=False))
        if hasattr(self._settings, "sync"):
            self._settings.sync()
        status = getattr(self._settings, "status", None)
        if callable(status):
            current = status()
            raw_status = getattr(current, "value", current)
            status_code = raw_status if isinstance(raw_status, int) else 0
            if status_code != 0:
                raise RuntimeError(f"ROUTE_PERSISTENCE_FAILED: {status_code}")

    def _publish(self, event_name: str, payload: dict) -> None:
        if self._event_bus is None:
            return
        for method_name in ("publish", "emit"):
            method = getattr(self._event_bus, method_name, None)
            if method is None:
                continue
            try:
                method(event_name, payload)
                return
            except Exception:
                logger.debug("Home-audio event publication failed", exc_info=True)

    @staticmethod
    def _stream_sample_format(stream: dict) -> tuple[int, int, int]:
        uri = stream.get("uri", {}) if isinstance(stream.get("uri"), dict) else {}
        raw = stream.get("sampleformat") or stream.get("sampleFormat") or uri.get("sampleFormat")
        if isinstance(raw, dict):
            return (
                int(raw.get("rate", 0) or 0),
                int(raw.get("bits", 0) or 0),
                int(raw.get("channels", 0) or 0),
            )
        if isinstance(raw, str):
            parts = raw.replace("/", ":").split(":")
            try:
                values = [int(part) for part in parts[:3]]
                while len(values) < 3:
                    values.append(0)
                return values[0], values[1], values[2]
            except ValueError:
                return 0, 0, 0
        return 0, 0, 0

    @classmethod
    def _normalise_stream(cls, stream: dict) -> dict:
        stream_id = str(stream.get("id", stream.get("stream_id", "")) or "")
        rate, bits, channels = cls._stream_sample_format(stream)
        status = str(stream.get("status", stream.get("state", "idle")) or "idle")
        codec = stream.get("codec", "")
        if isinstance(stream.get("uri"), dict):
            codec = codec or stream["uri"].get("codec", "")
        return {
            "id": stream_id,
            "name": stream.get("name") or stream_id or "Stream",
            "type": "snapcast_stream",
            "format": str(codec or "unknown"),
            "sample_rate": rate,
            "bit_depth": bits,
            "channels": channels,
            "uri": stream.get("uri", {}),
            "state": status,
            "routeable": bool(stream_id),
            "routable": bool(stream_id),
            "backend": "snapcast",
            "server_id": "snapcast_control",
        }

    @staticmethod
    def _normalise_group(group: dict, backend: str = "snapcast") -> dict:
        clients = group.get("clients", group.get("members", [])) or []
        member_ids = [
            str(member.get("id", "")) if isinstance(member, dict) else str(member)
            for member in clients
        ]
        stream_id = str(group.get("stream_id", group.get("streamId", "")) or "")
        group_id = str(group.get("id", "") or "")
        connected_members = [
            member for member in clients
            if isinstance(member, dict) and bool(member.get("connected"))
        ]
        return {
            "id": group_id,
            "name": group.get("name") or group_id or "Zona",
            "members": [member for member in member_ids if member],
            "devices": [member for member in member_ids if member],
            "stream_id": stream_id,
            "active": bool(group.get("active", stream_id)),
            "volume": group.get("volume", group.get("volume_level")),
            "muted": bool(group.get("muted", False)),
            "state": "playing" if stream_id else "configured",
            "backend": backend,
            "connected": bool(connected_members),
            "routeable": backend == "snapcast" and bool(group_id) and bool(connected_members),
            "routable": backend == "snapcast" and bool(group_id) and bool(connected_members),
            "server_id": "snapcast_control" if backend == "snapcast" else "",
        }

    def get_servers(self) -> list[dict]:
        """Return normalized local and remote Snapserver snapshots."""
        servers = []
        if self._snapserver is None:
            if self._snapcast is not None:
                servers.append(self._control_server_snapshot())
            return servers
        running = bool(getattr(self._snapserver, "is_running", False))
        binary_available = True
        availability = getattr(self._snapserver, "is_binary_available", None)
        if callable(availability):
            binary_available = bool(availability())
        state = str(getattr(self._snapserver, "state", "") or "")
        if not state:
            state = "running" if running else ("stopped" if binary_available else "unavailable")
        control_connected = bool(
            self._snapcast is not None and getattr(self._snapcast, "connected", False)
        )
        groups = self.get_groups() if control_connected else []
        streams = self.get_streams() if control_connected else []
        receivers = self.get_receivers() if control_connected else []
        servers.append(
            {
                "id": "local_snapserver",
                "name": "Snapserver local",
                "type": "snapserver",
                "host": "127.0.0.1",
                "tcp_port": int(getattr(self._snapserver, "tcp_port", 1704)),
                "control_port": int(getattr(self._snapserver, "control_port", 1705)),
                "http_port": int(getattr(self._snapserver, "http_port", 1780)),
                "binary_available": binary_available,
                "state": state,
                "error": str(getattr(self._snapserver, "last_error", "") or ""),
                "endpoint": f"127.0.0.1:{int(getattr(self._snapserver, 'control_port', 1705))}",
                "last_checked": self._last_refresh,
                "streams_count": len(streams),
                "groups_count": len(groups),
                "clients_count": len([item for item in receivers if item.get("connected")]),
            }
        )
        endpoint = str(getattr(self._snapcast, "endpoint", "") or "")
        if endpoint and not endpoint.startswith(("127.0.0.1:", "localhost:")):
            servers.append(self._control_server_snapshot())
        return servers

    def _control_server_snapshot(self) -> dict:
        endpoint = str(getattr(self._snapcast, "endpoint", "") or "")
        host, _, raw_port = endpoint.partition(":")
        connected = bool(getattr(self._snapcast, "connected", False))
        groups = self.get_groups() if connected else []
        streams = self.get_streams() if connected else []
        receivers = self.get_receivers() if connected else []
        return {
            "id": "snapcast_control",
            "name": "Servidor Snapcast configurado",
            "type": "snapserver_remote",
            "endpoint": endpoint,
            "host": host,
            "control_port": int(raw_port) if raw_port.isdigit() else 1705,
            "state": "active" if connected else "configured",
            "last_checked": self._last_refresh,
            "streams_count": len(streams),
            "groups_count": len(groups),
            "clients_count": len([item for item in receivers if item.get("connected")]),
            "error": str(getattr(self._snapcast, "last_error", "") or ""),
        }

    def enable_distribution(self) -> dict:
        """Start Snapserver and enable the FIFO distribution pipeline.

        Returns:
            {"ok": True, "fifo": True, "snapserver": True, "pipeline": True}
            or {"ok": False, "error": ..., "step": ...} on failure.
        """
        steps = {}

        # 1. Ensure FIFO exists
        from integrations.snapcast.fifo_manager import ensure_fifo, open_fifo
        fifo_ok = ensure_fifo()
        if not fifo_ok:
            return {"ok": False, "error": "FIFO_CREATE_FAILED", "step": "fifo"}
        steps["fifo"] = True

        # 2. Start Snapserver if not running
        if self._snapserver and not self._snapserver.is_running:
            result = self._snapserver.start()
            if not result.get("ok"):
                return {"ok": False, "error": result.get("error", "SNAPSERVER_START_FAILED"), "step": "snapserver"}
        steps["snapserver"] = True

        # 3. Open FIFO writer
        fd = open_fifo()
        if fd is None:
            import logging
            logging.getLogger("michi.home_audio").warning(
                "FIFO opened non-blocking — Snapserver may not have reader yet")
        steps["fifo_open"] = True

        # 4. Enable pipeline FIFO branch
        if self._playback and hasattr(self._playback, "set_snapcast_fifo"):
            try:
                self._playback.set_snapcast_fifo(True)
            except Exception as exc:
                return {"ok": False, "error": str(exc), "step": "pipeline"}
        steps["pipeline"] = True

        return {"ok": True, **steps}

    def disable_distribution(self) -> dict:
        """Stop distribution: disable FIFO pipeline, stop Snapserver."""
        steps = {}

        if self._playback and hasattr(self._playback, "set_snapcast_fifo"):
            try:
                self._playback.set_snapcast_fifo(False)
            except Exception as exc:
                steps["pipeline_error"] = str(exc)
            else:
                steps["pipeline"] = True

        from integrations.snapcast.fifo_manager import close_fifo
        close_fifo()
        steps["fifo_closed"] = True

        if self._snapserver and self._snapserver.is_running:
            result = self._snapserver.stop()
            steps["snapserver_stopped"] = result.get("ok", False)
        else:
            steps["snapserver_stopped"] = True

        return {"ok": True, **steps}

    def start_server(self, server_id: str = "local_snapserver") -> dict:
        """Start the owned local Snapserver and return verified state."""
        if server_id != "local_snapserver" or self._snapserver is None:
            return {"ok": False, "error": "SERVER_UNAVAILABLE"}
        if bool(getattr(self._snapserver, "is_running", False)):
            return {"ok": True, "state": "running", "already_running": True}
        availability = getattr(self._snapserver, "is_binary_available", None)
        if callable(availability) and not availability():
            return {"ok": False, "error": "SNAPSERVER_BINARY_UNAVAILABLE"}
        try:
            result = self._snapserver.start()
            if isinstance(result, dict):
                return result
            return {"ok": False, "error": "SNAPSERVER_START_NOT_VERIFIED"}
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def stop_server(self, server_id: str = "local_snapserver") -> dict:
        """Stop only Michi's owned local Snapserver process."""
        if server_id != "local_snapserver" or self._snapserver is None:
            return {"ok": False, "error": "SERVER_UNAVAILABLE"}
        if not bool(getattr(self._snapserver, "is_running", False)):
            return {"ok": True, "state": "stopped", "already_stopped": True}
        try:
            result = self._snapserver.stop()
            if isinstance(result, dict):
                return result
            return {"ok": False, "error": "SNAPSERVER_STOP_NOT_VERIFIED"}
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def get_streams(self) -> list[dict]:
        """Return normalized Snapcast streams, recording transport failures."""
        if self._snapcast is None:
            return []
        try:
            streams = self._snapcast.get_streams() or []
            self._last_refresh = time.time()
            return [self._normalise_stream(stream) for stream in streams]
        except Exception as exc:
            self._last_error = str(exc)
            logger.debug("Snapcast stream discovery failed", exc_info=True)
            return []

    def get_sources(self) -> list[dict]:
        """Return routeable streams plus truthful local-playback context."""
        sources = self.get_streams()
        if self._playback is not None:
            current = getattr(self._playback, "current", None)
            playback_state = getattr(self._playback, "state", None)
            is_playing = playback_state in ("playing", "PLAYING") if playback_state else bool(current)
            fifo_path = "/tmp/michi-snapfifo"
            fifo_ready = os.path.exists(fifo_path) and os.access(fifo_path, os.W_OK)
            snapcast_running = self._snapserver.is_running if self._snapserver else False
            routeable = fifo_ready and snapcast_running
            sources.append(
                {
                    "id": "local_playback",
                    "name": "Reproducción local de Michi",
                    "type": "local_playback",
                    "format": "runtime",
                    "sample_rate": 0,
                    "bit_depth": 0,
                    "channels": 0,
                    "state": "playing" if is_playing else "idle",
                    "routeable": routeable,
                    "routable": routeable,
                    "backend": "michi",
                    "reason": "" if routeable else "FIFO o Snapserver no disponible. Inicia la distribución para activar.",
                }
            )
        return sources

    def discover_receivers(self) -> list[dict]:
        """Refresh network discovery and return merged receiver state."""
        if self._discovery is not None:
            refresh = getattr(self._discovery, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception as exc:
                    self._last_error = str(exc)
                    logger.debug("Receiver discovery failed", exc_info=True)
        return self.get_receivers()

    def discover_home_assistant_instances(self) -> list[dict]:
        """Discover Home Assistant instances advertised through mDNS/Avahi."""
        avahi_browse = shutil.which("avahi-browse")
        if not avahi_browse:
            self._home_assistant_instances = []
            return []
        try:
            completed = subprocess.run(
                [
                    avahi_browse,
                    "--resolve",
                    "--terminate",
                    "--parsable",
                    "_home-assistant._tcp",
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self._last_error = str(exc)
            logger.debug("Home Assistant mDNS discovery failed", exc_info=True)
            self._home_assistant_instances = []
            return []

        instances: dict[tuple[str, int], dict] = {}
        for line in completed.stdout.splitlines():
            parts = line.split(";")
            if len(parts) < 9 or parts[0] != "=":
                continue
            try:
                port = int(parts[8])
            except ValueError:
                continue
            host = parts[7] or parts[6].rstrip(".")
            key = (host, port)
            instances[key] = {
                "name": parts[3] or "Home Assistant",
                "host": host,
                "hostname": parts[6].rstrip("."),
                "port": port,
                "url": f"http://{host}:{port}",
                "discovered_by": "mdns",
            }
        self._home_assistant_instances = list(instances.values())
        return deepcopy(self._home_assistant_instances)

    def get_home_assistant_instances(self) -> list[dict]:
        """Return the latest Home Assistant mDNS discovery snapshot."""
        return deepcopy(self._home_assistant_instances)

    def get_receivers(self) -> list[dict]:
        """Merge controlled and discovered receivers into one normalized list."""
        merged: dict[str, dict] = {}
        if self._snapcast is not None:
            try:
                for client in self._snapcast.get_client_list() or []:
                    client_id = str(client.get("id", "") or "")
                    if not client_id:
                        continue
                    merged[client_id] = {
                        **client,
                        "id": client_id,
                        "name": client.get("name") or client_id,
                        "state": "online" if client.get("connected") else "offline",
                        "available": bool(client.get("connected")),
                        "backend": "snapcast",
                        "last_activity": self._last_refresh,
                    }
                self._last_refresh = time.time()
            except Exception as exc:
                self._last_error = str(exc)
                logger.debug("Snapcast client query failed", exc_info=True)
        if self._discovery is not None:
            clients_method = getattr(self._discovery, "clients", None)
            try:
                discovered = clients_method() if callable(clients_method) else []
            except Exception:
                discovered = []
            for client in discovered or []:
                client_id = str(client.get("id", "") or "")
                if not client_id or client_id in merged:
                    continue
                merged[client_id] = {
                    **client,
                    "id": client_id,
                    "name": client.get("name") or client_id,
                    "connected": False,
                    "state": "discovered",
                    "available": bool(client.get("available", True)),
                    "volume": int(client.get("volume", 100) or 0),
                    "muted": bool(client.get("muted", False)),
                    "latency_ms": int(client.get("latency_ms", 0) or 0),
                    "backend": client.get("backend", "snapcast"),
                }
        return list(merged.values())

    def _get_ha_devices(self, *, imported_only: bool = False) -> list[dict]:
        if self._ha_client is None:
            return []
        getter = getattr(self._ha_client, "get_states", None)
        if getter is None:
            getter = getattr(self._ha_client, "get_devices", None)
        if not callable(getter):
            return []
        try:
            devices = getter() or []
        except Exception as exc:
            self._last_error = str(exc)
            return []
        normalised = []
        for device in devices:
            entity_id = str(device.get("entity_id", "") or "")
            imported = (
                self._selected_ha_entity_ids is None
                or entity_id in self._selected_ha_entity_ids
            )
            if imported_only and not imported:
                continue
            attributes = device.get("attributes", {}) or {}
            normalised.append(
                {
                    "id": entity_id,
                    "entity_id": entity_id,
                    "name": attributes.get("friendly_name") or device.get("name") or entity_id,
                    "state": device.get("state", "unknown"),
                    "volume": attributes.get("volume_level", 0.0),
                    "muted": bool(attributes.get("is_volume_muted", False)),
                    "backend": "home_assistant",
                    "imported": imported,
                }
            )
        return normalised

    def get_devices(self) -> list[dict]:
        return self._get_ha_devices()

    def import_home_assistant_entities(self, entity_ids: list[str]) -> dict:
        """Persist which discovered media-player entities become Michi zones."""
        selected = list(dict.fromkeys(str(entity_id) for entity_id in entity_ids))
        available = {device["entity_id"] for device in self._get_ha_devices()}
        unknown = [entity_id for entity_id in selected if entity_id not in available]
        if unknown:
            return {
                "ok": False,
                "error": "UNKNOWN_HOME_ASSISTANT_ENTITY",
                "unknown": unknown,
            }
        self._selected_ha_entity_ids = set(selected)
        self._settings.setValue(
            _HA_SELECTED_ENTITIES_KEY,
            json.dumps(selected, ensure_ascii=False),
        )
        if hasattr(self._settings, "sync"):
            self._settings.sync()
        return {"ok": True, "imported": selected, "count": len(selected)}

    def get_groups(self) -> list[dict]:
        """Return verified Snapcast groups or configured-group fallbacks."""
        if self._snapcast is not None:
            try:
                groups = self._snapcast.get_groups() or []
                self._last_refresh = time.time()
                return [self._normalise_group(group, "snapcast") for group in groups]
            except Exception as exc:
                self._last_error = str(exc)
                logger.debug("Snapcast group query failed", exc_info=True)
        if self._group_mgr is not None:
            getter = getattr(self._group_mgr, "groups", None)
            if getter is None:
                getter = getattr(self._group_mgr, "get_groups", None)
            if callable(getter):
                try:
                    return [
                        self._normalise_group(group, "configured")
                        for group in (getter() or [])
                    ]
                except Exception:
                    logger.debug("Configured group query failed", exc_info=True)
        return []

    def get_zones(self) -> list[dict]:
        """Combine Snapcast groups and Home Assistant devices as zones."""
        zones = self.get_groups()
        for device in self._get_ha_devices(imported_only=True):
            zones.append(
                {
                    "id": device["id"],
                    "name": device["name"],
                    "members": [device["id"]],
                    "devices": [device["id"]],
                    "stream_id": "",
                    "active": device.get("state") == "playing",
                    "volume": device.get("volume", 0.0),
                    "muted": device.get("muted", False),
                    "state": device.get("state", "unknown"),
                    "backend": "home_assistant",
                    "routeable": False,
                    "routable": False,
                }
            )
        return zones

    def discover_zones(self) -> list[dict]:
        self.discover_receivers()
        return self.get_zones()

    def get_destinations(self) -> list[dict]:
        destinations = []
        for group in self.get_groups():
            destinations.append(
                {
                    "id": group["id"],
                    "name": group["name"],
                    "type": "zone",
                    "backend": group["backend"],
                    "state": group["state"],
                    "stream_id": group["stream_id"],
                    "members": group["members"],
                    "routeable": bool(group.get("routeable")),
                    "routable": bool(group.get("routeable")),
                    "connected": bool(group.get("connected")),
                    "server_id": group.get("server_id", ""),
                }
            )
        return destinations

    def list_routes(self) -> list[dict]:
        return deepcopy(self._routes)

    def _route(self, route_id: str) -> dict | None:
        return next((route for route in self._routes if route.get("id") == route_id), None)

    def create_route(
        self,
        name: str,
        source_id: str,
        destination_ids: list[str],
    ) -> dict:
        """Validate and persist an inactive route configuration."""
        sources = {source["id"]: source for source in self.get_sources()}
        source = sources.get(source_id)
        if source is None:
            return {"ok": False, "error": "UNKNOWN_SOURCE"}
        if not source.get("routeable"):
            return {"ok": False, "error": "SOURCE_NOT_ROUTEABLE"}
        destinations = {destination["id"]: destination for destination in self.get_destinations()}
        selected = [destinations.get(destination_id) for destination_id in destination_ids]
        if not selected or any(destination is None for destination in selected):
            return {"ok": False, "error": "UNKNOWN_DESTINATION"}
        if any(not destination.get("routeable") for destination in selected if destination):
            return {"ok": False, "error": "DESTINATION_NOT_ROUTEABLE"}
        route = {
            "id": uuid4().hex,
            "name": name.strip() or f"{source['name']} → {len(selected)} destino(s)",
            "source_id": source_id,
            "destination_ids": list(dict.fromkeys(destination_ids)),
            "state": "configured",
            "latency_ms": 0,
            "error": "",
            "last_error": "",
            "destination_errors": {},
            "previous_streams": {},
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        self._routes.append(route)
        try:
            self._save_routes()
        except RuntimeError as exc:
            self._routes.remove(route)
            return {"ok": False, "error": "ROUTE_PERSISTENCE_FAILED", "message": str(exc)}
        self._publish("home_audio.route.created", deepcopy(route))
        return {"ok": True, "route": deepcopy(route)}

    def update_route(
        self,
        route_id: str,
        name: str,
        source_id: str,
        destination_ids: list[str],
        mode: str = "atomic",
    ) -> dict:
        """Update an inactive route under the requested transaction policy."""
        if mode not in _ROUTE_TRANSACTION_MODES:
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "INVALID_TRANSACTION_MODE",
            }
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "mode": mode, "degraded": [], "error": "UNKNOWN_ROUTE"}
        if route.get("state") in {"active", "degraded"}:
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "ACTIVE_ROUTE_MUST_BE_STOPPED",
            }
        sources = {source["id"]: source for source in self.get_sources()}
        if source_id not in sources:
            return {"ok": False, "mode": mode, "degraded": [], "error": "UNKNOWN_SOURCE"}
        if not sources[source_id].get("routeable"):
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "SOURCE_NOT_ROUTEABLE",
            }
        destinations = {destination["id"]: destination for destination in self.get_destinations()}
        unique_ids = list(dict.fromkeys(destination_ids))
        if not unique_ids:
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "UNKNOWN_DESTINATION",
            }

        rejected = []
        valid_ids = []
        for destination_id in unique_ids:
            destination = destinations.get(destination_id)
            if destination is None:
                rejected.append(
                    {"destination_id": destination_id, "error": "UNKNOWN_DESTINATION"}
                )
            elif not destination.get("routeable"):
                rejected.append(
                    {"destination_id": destination_id, "error": "DESTINATION_NOT_ROUTEABLE"}
                )
            else:
                valid_ids.append(destination_id)

        with RouteTransaction(mode=mode) as transaction:
            transaction.snapshot(route)
            for failure in rejected:
                transaction.fail(failure)
            if rejected and mode == "atomic":
                result = transaction.commit()
                result["error"] = rejected[0]["error"]
                return result
            if not valid_ids:
                result = transaction.rollback()
                result["error"] = rejected[0]["error"]
                return result

            route.update(
                name=name.strip() or route.get("name", "Ruta"),
                source_id=source_id,
                destination_ids=valid_ids,
                state="configured",
                previous_streams={},
                last_error="",
                destination_errors={},
                updated_at=int(time.time()),
            )
            try:
                self._save_routes()
            except RuntimeError as exc:
                result = transaction.rollback()
                result.update(error="ROUTE_PERSISTENCE_FAILED", message=str(exc))
                return result
            result = transaction.commit()
            result["route"] = deepcopy(route)
            return result

    def start_route(self, route_id: str, mode: str = "atomic") -> dict:
        """Activate destinations using atomic or best-effort semantics."""
        if mode not in _ROUTE_TRANSACTION_MODES:
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "INVALID_TRANSACTION_MODE",
            }
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "mode": mode, "degraded": [], "error": "UNKNOWN_ROUTE"}
        if self._snapcast is None:
            return self._route_start_precondition_error(
                route, mode, "SNAPCAST_CONTROL_UNAVAILABLE"
            )

        source = next(
            (item for item in self.get_sources() if item.get("id") == route.get("source_id")),
            None,
        )
        if source is None:
            return self._route_start_precondition_error(route, mode, "UNKNOWN_SOURCE")
        if not source.get("routeable"):
            return self._route_start_precondition_error(route, mode, "SOURCE_NOT_ROUTEABLE")

        groups = {group["id"]: group for group in self.get_groups()}
        previous = {}
        changed = []
        failures = []
        with RouteTransaction(mode=mode) as transaction:
            transaction.snapshot(route)
            for destination_id in route.get("destination_ids", []):
                group = groups.get(destination_id)
                if (
                    group is None
                    or group.get("backend") != "snapcast"
                    or not group.get("connected")
                ):
                    failures.append(
                        {"destination_id": destination_id, "error": "DESTINATION_OFFLINE"}
                    )
                    continue
                previous[destination_id] = group.get("stream_id", "")
                try:
                    self._snapcast.set_group_stream(destination_id, route["source_id"])
                    changed.append(destination_id)
                except Exception as exc:
                    failures.append({"destination_id": destination_id, "error": str(exc)})

            verified_groups = {group["id"]: group for group in self.get_groups()}
            failed_ids = {item["destination_id"] for item in failures}
            for destination_id in changed:
                if destination_id in failed_ids:
                    continue
                actual = verified_groups.get(destination_id, {}).get("stream_id", "")
                if actual != route["source_id"]:
                    failures.append(
                        {
                            "destination_id": destination_id,
                            "error": "ROUTE_VERIFICATION_FAILED",
                            "actual_stream": actual,
                        }
                    )

            for failure in failures:
                transaction.fail(failure)

            if failures and mode == "atomic":
                rollback_failures = self._restore_route_destinations(changed, previous)
                for failure in rollback_failures:
                    transaction.fail(failure)
                result = transaction.commit()
                self._record_route_start_result(route, failures + rollback_failures, {}, "error")
            else:
                successful = len(changed) - len(
                    {item["destination_id"] for item in failures if item["destination_id"] in changed}
                )
                state = "active" if not failures else ("degraded" if successful else "error")
                self._record_route_start_result(route, failures, previous, state)
                result = None

            try:
                self._save_routes()
            except RuntimeError as exc:
                if result is None:
                    self._restore_route_destinations(changed, previous)
                    result = transaction.rollback()
                result.update(error="ROUTE_PERSISTENCE_FAILED", message=str(exc))
                return result
            if result is None:
                result = transaction.commit()
                result["ok"] = not failures or (mode == "best_effort" and successful > 0)

        self._publish("home_audio.route.started", deepcopy(route))
        result.update(
            partial=bool(failures) and route["state"] == "degraded",
            failures=failures,
            route=deepcopy(route),
        )
        if failures and "error" not in result:
            result["error"] = failures[0]["error"]
        return result

    def _route_start_precondition_error(self, route: dict, mode: str, error: str) -> dict:
        route.update(state="error", error=error, last_error=error)
        try:
            self._save_routes()
        except RuntimeError as exc:
            return {
                "ok": False,
                "mode": mode,
                "degraded": [],
                "error": "ROUTE_PERSISTENCE_FAILED",
                "message": str(exc),
            }
        return {
            "ok": False,
            "mode": mode,
            "degraded": [],
            "error": error,
            "route": deepcopy(route),
        }

    def _restore_route_destinations(
        self, destination_ids: list[str], previous: dict[str, str]
    ) -> list[dict]:
        failures = []
        for destination_id in destination_ids:
            try:
                self._snapcast.set_group_stream(destination_id, previous[destination_id])
            except Exception as exc:
                failures.append(
                    {
                        "destination_id": destination_id,
                        "error": f"ROLLBACK_FAILED: {exc}",
                    }
                )
        if failures:
            return failures
        restored_groups = {group["id"]: group for group in self.get_groups()}
        for destination_id in destination_ids:
            if restored_groups.get(destination_id, {}).get("stream_id", "") != previous[
                destination_id
            ]:
                failures.append(
                    {"destination_id": destination_id, "error": "ROLLBACK_VERIFICATION_FAILED"}
                )
        return failures

    @staticmethod
    def _record_route_start_result(
        route: dict,
        failures: list[dict],
        previous: dict[str, str],
        state: str,
    ) -> None:
        route["previous_streams"] = previous
        route["updated_at"] = int(time.time())
        route["error"] = json.dumps(failures, ensure_ascii=False) if failures else ""
        route["last_error"] = route["error"]
        route["destination_errors"] = {
            item["destination_id"]: item["error"] for item in failures
        }
        route["state"] = state

    def stop_route(self, route_id: str) -> dict:
        """Restore and verify the previous stream for every route destination."""
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "error": "UNKNOWN_ROUTE"}
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        previous = route.get("previous_streams", {}) or {}
        if not previous:
            return {"ok": False, "error": "NO_PREVIOUS_ROUTE_STATE"}

        failures = []
        restored = []
        for destination_id in route.get("destination_ids", []):
            previous_stream = previous.get(destination_id, "")
            if not previous_stream:
                failures.append(
                    {"destination_id": destination_id, "error": "NO_PREVIOUS_STREAM"}
                )
                continue
            try:
                self._snapcast.set_group_stream(destination_id, previous_stream)
                restored.append(destination_id)
            except Exception as exc:
                failures.append({"destination_id": destination_id, "error": str(exc)})

        verified_groups = {group["id"]: group for group in self.get_groups()}
        for destination_id in list(restored):
            actual = verified_groups.get(destination_id, {}).get("stream_id", "")
            if actual != previous.get(destination_id):
                restored.remove(destination_id)
                failures.append(
                    {"destination_id": destination_id, "error": "RESTORE_VERIFICATION_FAILED"}
                )

        route["updated_at"] = int(time.time())
        route["error"] = json.dumps(failures, ensure_ascii=False) if failures else ""
        route["last_error"] = route["error"]
        route["destination_errors"] = {
            item["destination_id"]: item["error"] for item in failures
        }
        route["state"] = "stopped" if not failures else (
            "degraded" if restored else "error"
        )
        if not failures:
            route["previous_streams"] = {}
        try:
            self._save_routes()
        except RuntimeError as exc:
            return {
                "ok": False,
                "error": "ROUTE_PERSISTENCE_FAILED",
                "message": str(exc),
                "route": deepcopy(route),
            }
        self._publish("home_audio.route.stopped", deepcopy(route))
        return {
            "ok": not failures,
            "partial": bool(restored) and bool(failures),
            "restored": restored,
            "failures": failures,
            "route": deepcopy(route),
        }

    def delete_route(self, route_id: str) -> dict:
        """Delete an inactive route and persist the updated route list."""
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "error": "UNKNOWN_ROUTE"}
        if route.get("state") in {"active", "degraded"}:
            return {"ok": False, "error": "ACTIVE_ROUTE_MUST_BE_STOPPED"}
        previous_routes = self._routes
        self._routes = [item for item in self._routes if item.get("id") != route_id]
        try:
            self._save_routes()
        except RuntimeError as exc:
            self._routes = previous_routes
            return {"ok": False, "error": "ROUTE_PERSISTENCE_FAILED", "message": str(exc)}
        self._publish("home_audio.route.deleted", {"id": route_id})
        return {"ok": True, "deleted": route_id}

    def recover_route(self, route_id: str) -> dict:
        return self.start_route(route_id)

    def _receiver(self, receiver_id: str) -> dict | None:
        return next(
            (receiver for receiver in self.get_receivers() if receiver.get("id") == receiver_id),
            None,
        )

    def set_receiver_volume(self, receiver_id: str, volume: int) -> dict:
        """Set receiver volume and verify the resulting value."""
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not current.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        target = max(0, min(100, int(volume)))
        try:
            self._snapcast.set_client_volume(receiver_id, target, bool(current.get("muted")))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = self._receiver(receiver_id)
        if verified is None or int(verified.get("volume", -1)) != target:
            return {"ok": False, "error": "VOLUME_VERIFICATION_FAILED"}
        return {"ok": True, "receiver": verified}

    def set_receiver_mute(self, receiver_id: str, muted: bool) -> dict:
        """Set receiver mute and verify the resulting value."""
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not current.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        try:
            self._snapcast.set_client_volume(
                receiver_id,
                int(current.get("volume", 100) or 0),
                bool(muted),
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = self._receiver(receiver_id)
        if verified is None or bool(verified.get("muted")) != bool(muted):
            return {"ok": False, "error": "MUTE_VERIFICATION_FAILED"}
        return {"ok": True, "receiver": verified}

    def set_receiver_latency(self, receiver_id: str, latency_ms: int) -> dict:
        """Set receiver latency and verify the resulting value."""
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not current.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        target = max(0, int(latency_ms))
        try:
            self._snapcast.set_client_latency(receiver_id, target)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = self._receiver(receiver_id)
        if verified is None or int(verified.get("latency_ms", -1)) != target:
            return {"ok": False, "error": "LATENCY_VERIFICATION_FAILED"}
        return {"ok": True, "receiver": verified}

    def generate_test_tone(
        self,
        duration_ms: int = 500,
        frequency_hz: int = 440,
    ) -> dict:
        """Generate stereo PCM and write it through the Snapcast FIFO path."""
        from integrations.snapcast.fifo_manager import write_fifo

        duration_ms = max(50, min(2000, int(duration_ms)))
        frequency_hz = max(20, min(20000, int(frequency_hz)))
        sample_rate = 44100
        frame_count = sample_rate * duration_ms // 1000
        amplitude = 8192
        frames = bytearray(frame_count * 4)
        for index in range(frame_count):
            sample = round(
                amplitude * math.sin(2 * math.pi * frequency_hz * index / sample_rate)
            )
            struct.pack_into("<hh", frames, index * 4, sample, sample)
        written = write_fifo(bytes(frames))
        if written <= 0:
            return {"ok": False, "error": "FIFO_WRITE_FAILED", "bytes_written": 0}
        return {"ok": True, "bytes_written": written, "duration_ms": duration_ms}

    def generateTestTone(
        self,
        durationMs: int = 500,
        frequencyHz: int = 440,
    ) -> dict:
        """QML-compatible alias for generate_test_tone()."""
        return self.generate_test_tone(durationMs, frequencyHz)

    def measure_latency(self, receiver_id: str) -> dict:
        """Read receiver latency and measure the Snapcast control round trip."""
        started_at = time.perf_counter()
        receiver = self._receiver(receiver_id)
        control_rtt_ms = round((time.perf_counter() - started_at) * 1000)
        if receiver is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not receiver.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        return {
            "ok": True,
            "receiver_id": receiver_id,
            "receiver_name": receiver.get("name", receiver_id),
            "latency_ms": int(receiver.get("latency_ms", 0) or 0),
            "control_rtt_ms": control_rtt_ms,
        }

    def measureLatency(self, receiverId: str) -> dict:
        """QML-compatible alias for measure_latency()."""
        return self.measure_latency(receiverId)

    def set_receiver_name(self, receiver_id: str, name: str) -> dict:
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not current.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        if not name.strip():
            return {"ok": False, "error": "INVALID_RECEIVER_NAME"}
        try:
            self._snapcast.set_client_name(receiver_id, name.strip())
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = self._receiver(receiver_id)
        if verified is None or verified.get("name") != name.strip():
            return {"ok": False, "error": "NAME_VERIFICATION_FAILED"}
        return {"ok": True, "receiver": verified}

    def move_receiver(self, receiver_id: str, group_id: str) -> dict:
        """Move a connected receiver and verify its target group."""
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        receiver = self._receiver(receiver_id)
        if receiver is None:
            return {"ok": False, "error": "RECEIVER_NOT_FOUND"}
        if not receiver.get("connected"):
            return {"ok": False, "error": "RECEIVER_OFFLINE"}
        groups = {group["id"]: group for group in self.get_groups()}
        target = groups.get(group_id)
        if target is None:
            return {"ok": False, "error": "DESTINATION_NOT_FOUND"}
        current_group_id = receiver.get("group", "")
        try:
            if current_group_id and current_group_id in groups and current_group_id != group_id:
                old_members = [
                    item
                    for item in groups[current_group_id]["members"]
                    if item != receiver_id
                ]
                self._snapcast.set_group_clients(current_group_id, old_members)
            target_members = list(dict.fromkeys([*target.get("members", []), receiver_id]))
            self._snapcast.set_group_clients(group_id, target_members)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = self._receiver(receiver_id)
        if verified is None or verified.get("group") != group_id:
            return {"ok": False, "error": "GROUP_MOVE_VERIFICATION_FAILED"}
        return {"ok": True, "receiver": verified}

    def create_group(self, name: str, zone_ids: list[str]) -> dict:
        """Create a configured group and verify that it can be read back."""
        if self._group_mgr is None:
            return {"ok": False, "error": "GROUP_MANAGER_UNAVAILABLE"}
        add_group = getattr(self._group_mgr, "add_group", None)
        if not callable(add_group):
            return {"ok": False, "error": "GROUP_CREATION_UNSUPPORTED"}
        try:
            group_id = add_group(name, zone_ids)
            groups = self._group_mgr.groups()
            group = next((item for item in groups if item.get("id") == group_id), None)
            if group is None:
                return {"ok": False, "error": "GROUP_VERIFICATION_FAILED"}
            return {"ok": True, "group": self._normalise_group(group, "configured")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_group(self, group_id: str) -> dict:
        """Delete a configured group and verify its removal."""
        if self._group_mgr is None:
            return {"ok": False, "error": "GROUP_MANAGER_UNAVAILABLE"}
        remove = getattr(self._group_mgr, "remove_group", None)
        if not callable(remove):
            return {"ok": False, "error": "GROUP_DELETION_UNSUPPORTED"}
        try:
            remove(group_id)
            remaining = self._group_mgr.groups()
            if any(group.get("id") == group_id for group in remaining):
                return {"ok": False, "error": "GROUP_DELETION_NOT_VERIFIED"}
            return {"ok": True, "deleted": group_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_group_name(self, group_id: str, new_name: str) -> dict:
        """Rename a group through the available backend and verify it."""
        if self._snapcast is not None:
            try:
                self._snapcast.set_group_name(group_id, new_name)
                verified = next(
                    (group for group in self.get_groups() if group.get("id") == group_id),
                    None,
                )
                if verified and verified.get("name") == new_name:
                    return {"ok": True, "group": verified}
                return {"ok": False, "error": "GROUP_RENAME_NOT_VERIFIED"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if self._group_mgr is None:
            return {"ok": False, "error": "GROUP_MANAGER_UNAVAILABLE"}
        rename = getattr(self._group_mgr, "rename_group", None)
        if not callable(rename):
            return {"ok": False, "error": "GROUP_RENAME_UNSUPPORTED"}
        rename(group_id, new_name)
        group = next(
            (item for item in self._group_mgr.groups() if item.get("id") == group_id),
            None,
        )
        if group is None or group.get("name") != new_name:
            return {"ok": False, "error": "GROUP_RENAME_NOT_VERIFIED"}
        return {"ok": True, "group": self._normalise_group(group, "configured")}

    def group(self, zone_ids: str | list[str]) -> dict:
        if isinstance(zone_ids, str):
            members = [item.strip() for item in zone_ids.split(",") if item.strip()]
        else:
            members = [str(item) for item in zone_ids if str(item)]
        if not members:
            return {"ok": False, "error": "EMPTY_ZONES"}
        return self.create_group("Grupo", members)

    def ungroup(self, group_id: str) -> dict:
        return self.delete_group(group_id)

    def set_volume(self, zone_id: str, volume: float) -> dict:
        """Set zone volume through Home Assistant or connected receivers."""
        zone = next((item for item in self.get_zones() if item.get("id") == zone_id), None)
        if zone is None:
            return {"ok": False, "error": "UNKNOWN_ZONE"}
        if zone.get("backend") == "home_assistant" and self._ha_client is not None:
            return self._ha_client.set_volume(zone_id, float(volume))
        receivers = [
            receiver
            for receiver in self.get_receivers()
            if receiver.get("group") == zone_id and receiver.get("connected")
        ]
        if not receivers:
            if self._group_mgr is not None and hasattr(self._group_mgr, "set_volume"):
                self._group_mgr.set_volume(zone_id, float(volume))
                return {
                    "ok": True,
                    "configured": True,
                    "physical_applied": False,
                    "warning": "NO_CONNECTED_RECEIVERS",
                }
            return {"ok": False, "error": "NO_CONNECTED_RECEIVERS"}
        failures = []
        for receiver in receivers:
            result = self.set_receiver_volume(receiver["id"], round(float(volume) * 100))
            if not result.get("ok"):
                failures.append({"receiver_id": receiver["id"], "result": result})
        return {"ok": not failures, "failures": failures, "physical_applied": True}

    def set_mute(self, zone_id: str, muted: bool) -> dict:
        """Set zone mute through Home Assistant or connected receivers."""
        zone = next((item for item in self.get_zones() if item.get("id") == zone_id), None)
        if zone is None:
            return {"ok": False, "error": "UNKNOWN_ZONE"}
        if zone.get("backend") == "home_assistant" and self._ha_client is not None:
            return self._ha_client.mute(zone_id, bool(muted))
        receivers = [
            receiver
            for receiver in self.get_receivers()
            if receiver.get("group") == zone_id and receiver.get("connected")
        ]
        if not receivers:
            return {"ok": False, "error": "NO_CONNECTED_RECEIVERS"}
        failures = []
        for receiver in receivers:
            result = self.set_receiver_mute(receiver["id"], muted)
            if not result.get("ok"):
                failures.append({"receiver_id": receiver["id"], "result": result})
        return {"ok": not failures, "failures": failures}

    def set_latency(self, zone_id: str, latency_ms: int) -> dict:
        """Apply latency to every connected receiver in a zone."""
        receivers = [
            receiver
            for receiver in self.get_receivers()
            if receiver.get("group") == zone_id and receiver.get("connected")
        ]
        if not receivers:
            return {"ok": False, "error": "NO_CONNECTED_RECEIVERS"}
        failures = []
        for receiver in receivers:
            result = self.set_receiver_latency(receiver["id"], latency_ms)
            if not result.get("ok"):
                failures.append({"receiver_id": receiver["id"], "result": result})
        return {"ok": not failures, "failures": failures}

    def configure(self, host: str = "", port: int = 0, access_token: str = "") -> dict:
        """Configure the Home Assistant endpoint and access token."""
        if self._ha_client is None:
            return {"ok": False, "error": "HOME_ASSISTANT_UNAVAILABLE"}
        configure = getattr(self._ha_client, "configure", None)
        if not callable(configure):
            return {"ok": False, "error": "CONFIGURATION_UNSUPPORTED"}
        endpoint = f"{host.rstrip('/')}:{port}" if port else host.rstrip("/")
        try:
            configure(endpoint, access_token, websocket_port=port or 8123)
            self._settings.setValue("home_audio/ha_host", host.rstrip("/"))
            self._settings.setValue("home_audio/ha_port", port or 8123)
            self._settings.setValue("home_audio/ha_ws_port", port or 8123)
            self._settings.setValue("home_audio/ha_base_url", endpoint)
            self._settings.setValue("home_audio/ha_token", access_token)
            if hasattr(self._settings, "sync"):
                self._settings.sync()
            return {"ok": True, "configured": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def test_connection(self) -> dict:
        """Probe configured Snapcast and Home Assistant backends."""
        snapcast_ok = False
        ha_ok = False
        errors = []
        if self._snapcast is not None:
            try:
                snapcast_ok = bool(self._snapcast.ping())
                if not snapcast_ok:
                    errors.append("SNAPCAST_UNREACHABLE")
            except Exception as exc:
                errors.append(str(exc))
        if self._ha_client is not None:
            try:
                self._ha_client.get_states()
                ha_ok = bool(getattr(self._ha_client, "connected", False))
                if not ha_ok:
                    errors.append("HOME_ASSISTANT_UNREACHABLE")
            except Exception as exc:
                errors.append(str(exc))
        return {
            "ok": snapcast_ok or ha_ok,
            "snapcast": snapcast_ok,
            "home_assistant": ha_ok,
            "errors": errors,
        }

    def assign_stream(self, stream_id: str) -> dict:
        """Assign a stream to the active group and verify the readback."""
        active_group = None
        if self._group_mgr is not None:
            active_group = getattr(self._group_mgr, "active_group", None)
        if not active_group:
            return {"ok": False, "error": "NO_ACTIVE_GROUP"}
        group_id = active_group.get("id", "")
        if not group_id or self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        try:
            self._snapcast.set_group_stream(group_id, stream_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = next(
            (group for group in self.get_groups() if group.get("id") == group_id),
            None,
        )
        if verified is None or verified.get("stream_id") != stream_id:
            return {"ok": False, "error": "STREAM_ASSIGNMENT_NOT_VERIFIED"}
        return {"ok": True, "group": verified}

    def assign_source_to_zone(self, zone_id: str, source_id: str) -> dict:
        """Assign a Snapcast source to one zone and verify the readback."""
        if source_id not in {source["id"] for source in self.get_sources()}:
            return {
                "ok": False,
                "error": "UNKNOWN_SOURCE",
                "stream_id": "",
                "verified": False,
            }
        group = next(
            (item for item in self.get_groups() if item.get("id") == zone_id),
            None,
        )
        if group is None:
            return {
                "ok": False,
                "error": "UNKNOWN_DESTINATION",
                "stream_id": "",
                "verified": False,
            }
        if self._snapcast is None:
            return {
                "ok": False,
                "error": "SNAPCAST_CONTROL_UNAVAILABLE",
                "stream_id": group.get("stream_id", ""),
                "verified": False,
            }
        try:
            self._snapcast.set_group_stream(zone_id, source_id)
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "stream_id": group.get("stream_id", ""),
                "verified": False,
            }
        verified_group = next(
            (item for item in self.get_groups() if item.get("id") == zone_id),
            None,
        )
        actual_stream = str((verified_group or {}).get("stream_id", "") or "")
        verified = actual_stream == source_id
        return {
            "ok": verified,
            "stream_id": actual_stream,
            "verified": verified,
            **({} if verified else {"error": "STREAM_ASSIGNMENT_NOT_VERIFIED"}),
        }

    def update_group(self, group_id: str, name: str, receiver_ids: list[str]) -> dict:
        """Replace a Snapcast group's name and exact receiver membership."""
        current = next(
            (group for group in self.get_groups() if group.get("id") == group_id),
            None,
        )
        if current is None:
            return {"ok": False, "errors": ["GROUP_NOT_FOUND"]}
        if self._snapcast is None:
            return {"ok": False, "errors": ["SNAPCAST_CONTROL_UNAVAILABLE"]}
        try:
            if current.get("name") != name:
                self._snapcast.set_group_name(group_id, name)
            self._snapcast.set_group_clients(group_id, receiver_ids)
        except Exception as exc:
            return {"ok": False, "errors": [str(exc)]}
        verified = next(
            (group for group in self.get_groups() if group.get("id") == group_id),
            None,
        )
        errors = []
        if verified is None or verified.get("name") != name:
            errors.append("GROUP_RENAME_NOT_VERIFIED")
        if set((verified or {}).get("members", [])) != set(receiver_ids):
            errors.append("GROUP_MEMBERSHIP_NOT_VERIFIED")
        return {"ok": not errors, "errors": errors}

    def disconnect_home_assistant(self) -> dict:
        """Close the Home Assistant client and clear its credentials."""
        if self._ha_client is None:
            return {"ok": True, "disconnected": False}
        disconnect = getattr(self._ha_client, "disconnect_home_assistant", None)
        try:
            if callable(disconnect):
                disconnect()
            else:
                configure = getattr(self._ha_client, "configure", None)
                if not callable(configure):
                    return {"ok": False, "error": "DISCONNECT_UNSUPPORTED"}
                configure("", "")
            for key, value in (
                ("home_audio/ha_host", ""),
                ("home_audio/ha_base_url", ""),
                ("home_audio/ha_token", ""),
            ):
                self._settings.setValue(key, value)
            if hasattr(self._settings, "sync"):
                self._settings.sync()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "disconnected": True}

    def select_source(self, source: str) -> dict:
        if source not in {item["id"] for item in self.get_sources()}:
            return {"ok": False, "error": "UNKNOWN_SOURCE"}
        self._selected_source = source
        self._settings.setValue(_SELECTED_SOURCE_KEY, source)
        return {"ok": True, "source_id": source}

    def transfer_playback(self, from_zone: str, to_zone: str) -> dict:
        """Copy a source zone's stream to another zone and verify it."""
        groups = {group["id"]: group for group in self.get_groups()}
        source_group = groups.get(from_zone)
        target_group = groups.get(to_zone)
        if source_group is None or target_group is None:
            return {"ok": False, "error": "UNKNOWN_ZONE"}
        stream_id = source_group.get("stream_id", "")
        if not stream_id:
            return {"ok": False, "error": "SOURCE_ZONE_HAS_NO_STREAM"}
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        try:
            self._snapcast.set_group_stream(to_zone, stream_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        verified = next(
            (group for group in self.get_groups() if group.get("id") == to_zone),
            None,
        )
        if verified is None or verified.get("stream_id") != stream_id:
            return {"ok": False, "error": "TRANSFER_NOT_VERIFIED"}
        return {"ok": True, "from_zone": from_zone, "to_zone": to_zone, "stream_id": stream_id}

    def playback_transfer(self, zone_id: str) -> dict:
        if not self._selected_source:
            return {"ok": False, "error": "NO_SELECTED_SOURCE"}
        route = self.create_route(
            f"Transferencia a {zone_id}",
            self._selected_source,
            [zone_id],
        )
        if not route.get("ok"):
            return route
        return self.start_route(route["route"]["id"])

    def start(self) -> dict:
        return {"ok": True, "routes": len(self._routes)}

    def cancel(self) -> dict:
        return {"ok": True, "cancelled": True}

    def health(self) -> dict:
        """Return aggregate Home Audio backend and route health."""
        servers = self.get_servers()
        return {
            "available": self.available,
            "connected": self.is_connected(),
            "snapcast_control": bool(
                self._snapcast is not None and getattr(self._snapcast, "connected", False)
            ),
            "snapserver_running": any(server.get("state") == "running" for server in servers),
            "home_assistant": bool(
                self._ha_client is not None and getattr(self._ha_client, "connected", False)
            ),
            "routes": len(self._routes),
            "last_error": self._last_error,
            "last_refresh": self._last_refresh,
        }

    def shutdown(self) -> dict:
        self._save_routes()
        return {"ok": True}
