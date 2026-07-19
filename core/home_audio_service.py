"""Home-audio distribution domain service.

The service normalises Snapcast, Home Assistant and local zone-management
adapters behind one truthful contract.  A saved route is configuration only;
it becomes active exclusively after the target Snapcast groups are updated and
read back successfully.
"""

from __future__ import annotations

import json
import logging
import time
from copy import deepcopy
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QSettings

logger = logging.getLogger("michi.home_audio")

_ROUTES_KEY = "home_audio/distribution_routes_v1"
_SELECTED_SOURCE_KEY = "home_audio/selected_source"


class HomeAudioService:
    def __init__(
        self,
        snapcast_group_manager=None,
        snapcast_discovery=None,
        snapserver_manager=None,
        snapcast_control=None,
        ha_client=None,
        local_media_server=None,
        playback_service=None,
        event_bus=None,
        settings=None,
    ):
        self._group_mgr = snapcast_group_manager
        self._event_bus = event_bus
        self._discovery = snapcast_discovery
        self._snapserver = snapserver_manager
        self._snapcast = snapcast_control
        self._ha_client = ha_client
        self._local_media = local_media_server
        self._playback = playback_service
        self._settings = settings or QSettings("Michi", "MusicPlayer")
        self._routes: list[dict] = []
        self._selected_source = str(self._settings.value(_SELECTED_SOURCE_KEY, "") or "")
        self._last_error = ""
        self._last_refresh = 0.0
        self._load_routes()

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
    def server_handoff_available(self) -> bool:
        return self._local_media is not None and hasattr(self._local_media, "handoff")

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
        except (TypeError, ValueError):
            logger.warning("Invalid persisted home-audio routes; resetting them")
            self._routes = []

    def _save_routes(self) -> None:
        self._settings.setValue(_ROUTES_KEY, json.dumps(self._routes, ensure_ascii=False))
        if hasattr(self._settings, "sync"):
            self._settings.sync()

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
            "state": status,
            "routeable": bool(stream_id),
            "backend": "snapcast",
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
            "routeable": backend == "snapcast" and bool(group_id),
        }

    def get_servers(self) -> list[dict]:
        if self._snapserver is None:
            return []
        running = bool(getattr(self._snapserver, "is_running", False))
        binary_available = True
        availability = getattr(self._snapserver, "is_binary_available", None)
        if callable(availability):
            binary_available = bool(availability())
        state = "running" if running else ("stopped" if binary_available else "unavailable")
        return [
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
            }
        ]

    def start_server(self, server_id: str = "local_snapserver") -> dict:
        if server_id != "local_snapserver" or self._snapserver is None:
            return {"ok": False, "error": "SERVER_UNAVAILABLE"}
        if bool(getattr(self._snapserver, "is_running", False)):
            return {"ok": True, "state": "running", "already_running": True}
        availability = getattr(self._snapserver, "is_binary_available", None)
        if callable(availability) and not availability():
            return {"ok": False, "error": "SNAPSERVER_BINARY_UNAVAILABLE"}
        try:
            self._snapserver.start()
            return {"ok": True, "state": "starting"}
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def stop_server(self, server_id: str = "local_snapserver") -> dict:
        if server_id != "local_snapserver" or self._snapserver is None:
            return {"ok": False, "error": "SERVER_UNAVAILABLE"}
        if not bool(getattr(self._snapserver, "is_running", False)):
            return {"ok": True, "state": "stopped", "already_stopped": True}
        try:
            self._snapserver.stop()
            still_running = bool(getattr(self._snapserver, "is_running", False))
            return {"ok": True, "state": "stopping" if still_running else "stopped"}
        except Exception as exc:
            self._last_error = str(exc)
            return {"ok": False, "error": str(exc)}

    def get_streams(self) -> list[dict]:
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
        sources = self.get_streams()
        if self._playback is not None:
            current = getattr(self._playback, "current_track", None)
            if callable(current):
                try:
                    current = current()
                except Exception:
                    current = None
            sources.append(
                {
                    "id": "local_playback",
                    "name": "Reproducción local de Michi",
                    "type": "local_playback",
                    "format": "runtime",
                    "sample_rate": 0,
                    "bit_depth": 0,
                    "channels": 0,
                    "state": "playing" if current else "idle",
                    "routeable": False,
                    "backend": "michi",
                    "reason": "El motor local aún no está conectado a un stream Snapcast",
                }
            )
        return sources

    def discover_receivers(self) -> list[dict]:
        if self._discovery is not None:
            refresh = getattr(self._discovery, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception as exc:
                    self._last_error = str(exc)
                    logger.debug("Receiver discovery failed", exc_info=True)
        return self.get_receivers()

    def get_receivers(self) -> list[dict]:
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

    def _get_ha_devices(self) -> list[dict]:
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
                }
            )
        return normalised

    def get_devices(self) -> list[dict]:
        return self._get_ha_devices()

    def get_groups(self) -> list[dict]:
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
        zones = self.get_groups()
        for device in self._get_ha_devices():
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
            "previous_streams": {},
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        self._routes.append(route)
        self._save_routes()
        self._publish("home_audio.route.created", deepcopy(route))
        return {"ok": True, "route": deepcopy(route)}

    def start_route(self, route_id: str) -> dict:
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "error": "UNKNOWN_ROUTE"}
        if self._snapcast is None:
            route.update(state="error", error="SNAPCAST_CONTROL_UNAVAILABLE")
            self._save_routes()
            return {"ok": False, "error": route["error"], "route": deepcopy(route)}

        groups = {group["id"]: group for group in self.get_groups()}
        previous = {}
        failures = []
        for destination_id in route.get("destination_ids", []):
            group = groups.get(destination_id)
            if group is None or group.get("backend") != "snapcast":
                failures.append({"destination_id": destination_id, "error": "DESTINATION_OFFLINE"})
                continue
            previous[destination_id] = group.get("stream_id", "")
            try:
                self._snapcast.set_group_stream(destination_id, route["source_id"])
            except Exception as exc:
                failures.append({"destination_id": destination_id, "error": str(exc)})

        verified_groups = {group["id"]: group for group in self.get_groups()}
        for destination_id in route.get("destination_ids", []):
            if any(item["destination_id"] == destination_id for item in failures):
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

        route["previous_streams"] = previous
        route["updated_at"] = int(time.time())
        route["error"] = json.dumps(failures, ensure_ascii=False) if failures else ""
        route["state"] = "active" if not failures else (
            "degraded" if len(failures) < len(route.get("destination_ids", [])) else "error"
        )
        self._save_routes()
        self._publish("home_audio.route.started", deepcopy(route))
        return {
            "ok": not failures,
            "partial": bool(failures) and route["state"] == "degraded",
            "failures": failures,
            "route": deepcopy(route),
        }

    def stop_route(self, route_id: str) -> dict:
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
        route["state"] = "stopped" if not failures else (
            "degraded" if restored else "error"
        )
        if not failures:
            route["previous_streams"] = {}
        self._save_routes()
        self._publish("home_audio.route.stopped", deepcopy(route))
        return {
            "ok": not failures,
            "partial": bool(restored) and bool(failures),
            "restored": restored,
            "failures": failures,
            "route": deepcopy(route),
        }

    def delete_route(self, route_id: str) -> dict:
        route = self._route(route_id)
        if route is None:
            return {"ok": False, "error": "UNKNOWN_ROUTE"}
        if route.get("state") in {"active", "degraded"}:
            return {"ok": False, "error": "ACTIVE_ROUTE_MUST_BE_STOPPED"}
        self._routes = [item for item in self._routes if item.get("id") != route_id]
        self._save_routes()
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
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None or not current.get("connected"):
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
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None or not current.get("connected"):
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
        if self._snapcast is None:
            return {"ok": False, "error": "SNAPCAST_CONTROL_UNAVAILABLE"}
        current = self._receiver(receiver_id)
        if current is None or not current.get("connected"):
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

    def create_group(self, name: str, zone_ids: list[str]) -> dict:
        if self._group_mgr is None:
            return {"ok": False, "error": "GROUP_MANAGER_UNAVAILABLE"}
        add_group = getattr(self._group_mgr, "add_group", None)
        if not callable(add_group):
            return {"ok": False, "error": "GROUP_CREATION_UNSUPPORTED"}
        try:
            group_id = add_group(name, zone_ids)
            groups = getattr(self._group_mgr, "groups")()
            group = next((item for item in groups if item.get("id") == group_id), None)
            if group is None:
                return {"ok": False, "error": "GROUP_VERIFICATION_FAILED"}
            return {"ok": True, "group": self._normalise_group(group, "configured")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_group(self, group_id: str) -> dict:
        if self._group_mgr is None:
            return {"ok": False, "error": "GROUP_MANAGER_UNAVAILABLE"}
        remove = getattr(self._group_mgr, "remove_group", None)
        if not callable(remove):
            return {"ok": False, "error": "GROUP_DELETION_UNSUPPORTED"}
        try:
            remove(group_id)
            remaining = getattr(self._group_mgr, "groups")()
            if any(group.get("id") == group_id for group in remaining):
                return {"ok": False, "error": "GROUP_DELETION_NOT_VERIFIED"}
            return {"ok": True, "deleted": group_id}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_group_name(self, group_id: str, new_name: str) -> dict:
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
            (item for item in getattr(self._group_mgr, "groups")() if item.get("id") == group_id),
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
        if self._ha_client is None:
            return {"ok": False, "error": "HOME_ASSISTANT_UNAVAILABLE"}
        configure = getattr(self._ha_client, "configure", None)
        if not callable(configure):
            return {"ok": False, "error": "CONFIGURATION_UNSUPPORTED"}
        endpoint = f"{host.rstrip('/')}:{port}" if port else host.rstrip("/")
        try:
            configure(endpoint, access_token)
            return {"ok": True, "configured": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def test_connection(self) -> dict:
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

    def select_source(self, source: str) -> dict:
        if source not in {item["id"] for item in self.get_sources()}:
            return {"ok": False, "error": "UNKNOWN_SOURCE"}
        self._selected_source = source
        self._settings.setValue(_SELECTED_SOURCE_KEY, source)
        return {"ok": True, "source_id": source}

    def transfer_playback(self, from_zone: str, to_zone: str) -> dict:
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

    def server_handoff(self) -> dict:
        if not self.server_handoff_available:
            return {"ok": False, "error": "HANDOFF_UNAVAILABLE"}
        result = self._local_media.handoff()
        return result if isinstance(result, dict) else {"ok": bool(result)}

    def handoff(self) -> dict:
        return self.server_handoff()

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

    def start(self):
        return {"ok": True, "routes": len(self._routes)}

    def cancel(self):
        return None

    def health(self) -> dict:
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

    def shutdown(self):
        self._save_routes()
        return {"ok": True}
