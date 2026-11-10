"""MQTT Device Discovery adapter for Home Assistant (E11.5-D).

Home Assistant 2026 does not expose ``media_player`` as an MQTT Discovery
component.  Michi therefore publishes a *device* bundle made exclusively from
supported MQTT components (sensor/button/number/switch/binary_sensor).  The
adapter remains deliberately narrow: it serializes state and emits a bounded
set of control intents to the Michi control plane; it never owns playback,
Home trust or device administration.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from michi_ecosystem.domain.device_registry import (
    DeviceCapability,
    DeviceDescriptor,
    DeviceType,
)
from michi_ecosystem.domain.home_assistant import (
    HomeAssistantConnectionState,
    state_from_transport_event,
)
from michi_ecosystem.ports.home_automation import MqttTransportPort

_ALLOWED_COMMANDS = frozenset({"play", "pause", "next", "previous", "volume", "mute"})
_FORBIDDEN_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "private_key",
    "privatekey",
    "bearer",
    "authorization",
    "access_token",
    "refresh_token",
    "session_token",
    "api_token",
    "client_secret",
    "home_root",
    "wifi_psk",
)


class HomeAssistantAdapterError(RuntimeError):
    """The external automation adapter rejected an invalid operation."""


class MqttHomeAssistantAdapter:
    def __init__(
        self,
        transport: MqttTransportPort,
        *,
        command_sink: Callable[[str, str, Any], None],
        discovery_prefix: str = "homeassistant",
        node_id: str = "michi",
        origin_version: str = "e11.5",
        cleanup_journal_path: Path | None = None,
    ) -> None:
        self._transport = transport
        self._command_sink = command_sink
        self._discovery_prefix = discovery_prefix.strip("/") or "homeassistant"
        self._node_id = self._safe_token(node_id) or "michi"
        self._origin_version = origin_version
        self._started = False
        self._lock = threading.RLock()
        self._devices: dict[str, DeviceDescriptor] = {}
        self._states: dict[str, dict[str, Any]] = {}
        self._home: dict[str, Any] | None = None
        # Connectivity is reported by the transport when it supports it; a
        # successful start is not evidence of a live link over time.
        self._connection = HomeAssistantConnectionState.DISABLED
        self._last_publish_ok_ms: float | None = None
        self._last_error_code = ""
        self._state_listener: Callable[[HomeAssistantConnectionState], None] | None = (
            None
        )
        # Invalidate late transport callbacks after stop()/failed start().
        self._generation = 0
        # In-process recovery journal for failed retained MQTT deletions.
        # Must be persisted by a host-owned store before it is restart-durable.
        self._cleanup_journal_path = (
            Path(cleanup_journal_path) if cleanup_journal_path is not None else None
        )
        self._pending_retained_cleanup: set[str] = self._load_cleanup_journal()

    def _load_cleanup_journal(self) -> set[str]:
        path = self._cleanup_journal_path
        if path is None or not path.exists():
            return set()
        if path.is_symlink():
            raise HomeAssistantAdapterError("MQTT cleanup journal cannot be a symlink")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or len(payload) > 4096:
                raise ValueError("invalid cleanup journal")
            topics = set()
            for topic in payload:
                if (
                    not isinstance(topic, str)
                    or len(topic) > 512
                    or not (
                        topic.startswith(f"michi/{self._node_id}/")
                        or topic.startswith(
                            f"{self._discovery_prefix}/device/{self._node_id}/"
                        )
                    )
                ):
                    raise ValueError("invalid retained cleanup topic")
                topics.add(topic)
            return topics
        except (OSError, ValueError, TypeError) as exc:
            raise HomeAssistantAdapterError("invalid MQTT cleanup journal") from exc

    def _persist_cleanup_locked(self) -> None:
        # Called under self._lock. Optional host-provided path keeps the core
        # free of assumptions about platform credentials or file locations.
        path = self._cleanup_journal_path
        if path is None:
            return
        parent = path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink():
            raise HomeAssistantAdapterError("MQTT cleanup journal cannot be a symlink")
        fd, temp = tempfile.mkstemp(prefix=".michi-cleanup-", dir=parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(
                    sorted(self._pending_retained_cleanup),
                    output,
                    separators=(",", ":"),
                )
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    @property
    def started(self) -> bool:
        with self._lock:
            return self._started

    # ── connectivity (E12.1) ────────────────────────────────────────────

    def connection_state(self) -> HomeAssistantConnectionState:
        with self._lock:
            return self._connection

    def last_publish_ok_ms(self) -> float | None:
        with self._lock:
            return self._last_publish_ok_ms

    def last_error_code(self) -> str:
        with self._lock:
            return self._last_error_code

    def set_state_listener(
        self, listener: Callable[[HomeAssistantConnectionState], None] | None
    ) -> None:
        """Register a thread-agnostic connectivity listener (may fire off-GUI)."""
        with self._lock:
            self._state_listener = listener

    def _set_connection(self, state: HomeAssistantConnectionState) -> None:
        with self._lock:
            if self._connection is state:
                return
            self._connection = state
            listener = self._state_listener
        if listener is not None:
            # A listener failure must never break the MQTT callback thread.
            with contextlib.suppress(Exception):
                listener(state)

    def _on_transport_state(self, event: object, generation: int | None = None) -> None:
        state = state_from_transport_event(event)
        if state is None:
            return
        with self._lock:
            if generation is not None and generation != self._generation:
                return  # stale event from a previous start/stop cycle
            if not self._started:
                return
            if state is HomeAssistantConnectionState.CONNECTED:
                self._last_error_code = ""
            elif state is HomeAssistantConnectionState.ERROR:
                self._last_error_code = "BROKER_CONNECTION_ERROR"
        self._set_connection(state)

    def _mark_publish_ok(self) -> None:
        with self._lock:
            self._last_publish_ok_ms = time.time() * 1000.0

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._generation += 1
            generation = self._generation
            self._last_error_code = ""
            # Claim the start before transport hooks so a synchronous
            # "connected" event emitted during connect() is accepted (one
            # generation, never a stale callback).
            self._started = True
        self._set_connection(HomeAssistantConnectionState.CONNECTING)
        try:
            # Observers BEFORE connect: transports may emit connectivity
            # events during the connect call itself.
            state_hook = getattr(self._transport, "set_state_callback", None)
            if callable(state_hook):
                state_hook(lambda event: self._on_transport_state(event, generation))
            reconnect_hook = getattr(self._transport, "set_reconnect_callback", None)
            if callable(reconnect_hook):
                reconnect_hook(lambda: self._on_reconnect(generation))
            self._transport.connect()
            self._subscribe_runtime_topics()
            self._flush_pending_cleanup()
            # Initial retained discovery is part of startup. If this fails,
            # the broker connection must be torn down, not left half-active.
            self.republish()
            with self._lock:
                observed = self._connection in {
                    HomeAssistantConnectionState.CONNECTED,
                    HomeAssistantConnectionState.RECONNECTING,
                }
            if not observed:
                # No transport evidence: UNKNOWN is honest. CONNECTED is only
                # reported when the transport observed the link.
                self._set_connection(HomeAssistantConnectionState.UNKNOWN)
        except Exception:
            # A half-started MQTT integration is worse than an explicit OFF state.
            with self._lock:
                self._started = False
                self._generation += 1  # invalidate late callbacks
                # Normalized code only: exception text may carry broker URLs or
                # credentials and must never reach the UI or logs.
                self._last_error_code = "BROKER_CONNECT_FAILED"
            with contextlib.suppress(Exception):
                self._transport.disconnect()
            self._set_connection(HomeAssistantConnectionState.ERROR)
            raise

    def _subscribe_runtime_topics(self) -> None:
        self._transport.subscribe(
            f"michi/{self._node_id}/+/command/+", self._on_message
        )
        # HA publishes a birth message after its MQTT integration starts. A
        # fresh discovery/state replay here makes HA restarts self-healing.
        self._transport.subscribe("homeassistant/status", self._on_birth)

    def _on_reconnect(self, generation: int | None = None) -> None:
        """Optional MQTT transport callback after a broker reconnect."""
        with self._lock:
            if generation is not None and generation != self._generation:
                return
            if not self._started:
                return
        self._subscribe_runtime_topics()
        self.republish()
        self._set_connection(HomeAssistantConnectionState.CONNECTED)

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            # Invalidate callbacks immediately: a late disconnect event must
            # not resurrect a stopped integration. ``_started`` stays True
            # until retained tombstones are published below.
            self._generation += 1
        # Queue ALL deletions before broker I/O, so a disconnect during the
        # first device cannot discard the remaining cleanup obligations.
        with self._lock:
            pending_devices = tuple(self._devices.values())
            pending_home = (
                str(self._home["home_id"]) if self._home is not None else None
            )
            for device in pending_devices:
                self._pending_retained_cleanup.update(
                    self._device_tombstone_topics(device)
                )
            if pending_home:
                self._pending_retained_cleanup.update(
                    self._home_tombstone_topics(pending_home)
                )
            self._persist_cleanup_locked()
        try:
            # Disable means disable: remove retained discovery payloads before
            # broker disconnect so Home Assistant cannot resurrect ghost entities.
            for device in tuple(self._devices.values()):
                self._publish_availability(device, False)
                self._remove_device_discovery(device)
            if self._home is not None:
                self._remove_home_discovery(str(self._home["home_id"]))
        finally:
            try:
                self._transport.disconnect()
            finally:
                with self._lock:
                    self._started = False
                # Do not replay old retained entities after an OFF interval.
                # The service will rebuild the current projection on enable().
                with self._lock:
                    self._devices.clear()
                    self._states.clear()
                    self._home = None
                    self._last_error_code = ""
                self._set_connection(HomeAssistantConnectionState.DISABLED)

    def republish(self) -> None:
        """Re-advertise full discovery + last known state after reconnect/birth."""
        if not self._started:
            return
        self._flush_pending_cleanup()
        with self._lock:
            devices = tuple(self._devices.values())
            states = {key: dict(value) for key, value in self._states.items()}
            home = dict(self._home) if self._home is not None else None
        for device in devices:
            self._publish_device_discovery(device)
            state = states.get(device.canonical_id)
            if state is not None:
                self._publish_state_topics(device, state)
        if home is not None:
            self._publish_home_discovery(home)
            self._publish_home_state(home)
        if devices or home is not None:
            self._mark_publish_ok()

    @staticmethod
    def _safe_token(value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)

    @classmethod
    def _entity_key(cls, device: DeviceDescriptor) -> str:
        identity = device.michi_id or device.canonical_id
        readable = cls._safe_token(identity)[:48].strip("_") or "device"
        # Keep IDs stable while eliminating sanitization collisions (a-b / a_b).
        digest = hashlib.blake2s(identity.encode("utf-8"), digest_size=5).hexdigest()
        return f"{readable}_{digest}"

    def _device_topic(self, device: DeviceDescriptor) -> str:
        key = self._entity_key(device)
        return f"{self._discovery_prefix}/device/{self._node_id}/{key}/config"

    def _base(self, device: DeviceDescriptor) -> str:
        return f"michi/{self._node_id}/{self._entity_key(device)}"

    def _origin(self) -> dict[str, str]:
        return {"name": "Michi Ecosystem", "sw_version": self._origin_version}

    def publish_device(self, device: DeviceDescriptor) -> None:
        if not device.home_assistant_allowed:
            self.remove_device(device.canonical_id)
            return
        with self._lock:
            self._devices[device.canonical_id] = device
            started = self._started
            state = self._states.get(device.canonical_id)
        if started:
            self._publish_device_discovery(device)
            if state is not None:
                self._publish_state_topics(device, state)
            self._mark_publish_ok()

    def _publish_device_discovery(self, device: DeviceDescriptor) -> None:
        key = self._entity_key(device)
        base = self._base(device)
        identifier = f"michi_{key}"
        device_block: dict[str, Any] = {
            "identifiers": [identifier],
            "name": device.name,
            "manufacturer": "Michi",
            "model": device.type.value,
        }
        if device.app_or_firmware_version:
            device_block["sw_version"] = device.app_or_firmware_version

        components: dict[str, dict[str, Any]] = {
            "status": self._sensor_component(
                device, key, "status", "Estado", f"{base}/state/status"
            )
        }
        if DeviceCapability.PLAYBACK_ENDPOINT in device.capabilities:
            for command, label in (
                ("play", "Reproducir"),
                ("pause", "Pausar"),
                ("next", "Siguiente"),
                ("previous", "Anterior"),
            ):
                components[command] = {
                    "platform": "button",
                    "name": label,
                    "unique_id": f"michi_{key}_{command}",
                    "command_topic": f"{base}/command/{command}",
                    "payload_press": command,
                }
            components["volume"] = {
                "platform": "number",
                "name": "Volumen",
                "unique_id": f"michi_{key}_volume",
                "command_topic": f"{base}/command/volume",
                "state_topic": f"{base}/state/volume",
                "min": 0,
                "max": 100,
                "step": 1,
                "mode": "slider",
            }
            components["mute"] = {
                "platform": "switch",
                "name": "Silencio",
                "unique_id": f"michi_{key}_mute",
                "command_topic": f"{base}/command/mute",
                "state_topic": f"{base}/state/mute",
                "payload_on": "true",
                "payload_off": "false",
                "state_on": "true",
                "state_off": "false",
            }

        if device.type is DeviceType.DESKTOP_PLAYER:
            components.update(
                {
                    "output": self._sensor_component(
                        device, key, "output", "Salida", f"{base}/state/output"
                    ),
                    "codec": self._sensor_component(
                        device, key, "codec", "Codec", f"{base}/state/codec"
                    ),
                    "sample_rate": self._sensor_component(
                        device,
                        key,
                        "sample_rate",
                        "Sample rate",
                        f"{base}/state/sample_rate",
                    ),
                }
            )
        elif device.type is DeviceType.MICRO_SERVER:
            components.update(
                {
                    "clients": self._sensor_component(
                        device, key, "clients", "Clientes", f"{base}/state/clients"
                    ),
                    "health": self._sensor_component(
                        device, key, "health", "Salud", f"{base}/state/health"
                    ),
                }
            )
        elif device.type is DeviceType.MUSIC_STREAM:
            components["firmware"] = self._sensor_component(
                device, key, "firmware", "Firmware", f"{base}/state/firmware"
            )

        payload = {
            "device": device_block,
            "origin": self._origin(),
            "availability_topic": f"{base}/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
            "components": components,
        }
        self._publish_json(self._device_topic(device), payload, retain=True)
        self._publish_availability(device, device.online)

    @staticmethod
    def _sensor_component(
        _device: DeviceDescriptor, key: str, component: str, name: str, topic: str
    ) -> dict[str, Any]:
        return {
            "platform": "sensor",
            "name": name,
            "unique_id": f"michi_{key}_{component}",
            "state_topic": topic,
        }

    def publish_state(self, canonical_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            device = self._devices.get(canonical_id)
        if device is None:
            return
        safe = self._sanitize_state(state)
        if not isinstance(safe, dict):
            raise HomeAssistantAdapterError("device state must serialize as an object")
        with self._lock:
            self._states[canonical_id] = safe
            started = self._started
        if started:
            self._publish_state_topics(device, safe)
            self._mark_publish_ok()

    def _publish_state_topics(
        self, device: DeviceDescriptor, state: Mapping[str, Any]
    ) -> None:
        base = self._base(device)
        for field in (
            "status",
            "volume",
            "mute",
            "output",
            "codec",
            "sample_rate",
            "clients",
            "health",
            "firmware",
        ):
            if field not in state:
                continue
            value = state[field]
            if isinstance(value, bool):
                payload = "true" if value else "false"
            elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
                payload = str(value)
            else:
                continue
            self._transport.publish(f"{base}/state/{field}", payload, retain=True)
        # Diagnostic aggregate is useful for broker inspection but is not a HA
        # entity and remains secret-sanitized.
        self._publish_json(f"{base}/state_json", dict(state), retain=True)

    def remove_device(self, canonical_id: str) -> None:
        with self._lock:
            device = self._devices.pop(canonical_id, None)
            self._states.pop(canonical_id, None)
            started = self._started
        if device is None or not started:
            return
        try:
            self._publish_availability(device, False)
        finally:
            # Even a failed offline availability publish must queue the entire
            # tombstone set before the transport disappears.
            self._remove_device_discovery(device)

    @property
    def pending_cleanup_count(self) -> int:
        """Tombstones still awaiting an online broker acknowledgement."""
        with self._lock:
            return len(self._pending_retained_cleanup)

    def _purge_retained(self, topics: tuple[str, ...]) -> None:
        # Queue EVERY tombstone before I/O: a mid-batch disconnect must not
        # silently lose the remaining topics.
        with self._lock:
            self._pending_retained_cleanup.update(topics)
            self._persist_cleanup_locked()
        self._flush_pending_cleanup()

    def _flush_pending_cleanup(self) -> None:
        with self._lock:
            if not self._started:
                return
            pending = tuple(sorted(self._pending_retained_cleanup))
        for topic in pending:
            self._transport.publish(topic, "", retain=True)
            with self._lock:
                self._pending_retained_cleanup.discard(topic)
                self._persist_cleanup_locked()

    def _device_tombstone_topics(self, device: DeviceDescriptor) -> tuple[str, ...]:
        base = self._base(device)
        return (
            (self._device_topic(device),)
            + tuple(
                f"{base}/state/{key}"
                for key in (
                    "status",
                    "volume",
                    "mute",
                    "output",
                    "codec",
                    "sample_rate",
                    "clients",
                    "health",
                    "firmware",
                )
            )
            + (f"{base}/state_json", f"{base}/availability")
        )

    def _remove_device_discovery(self, device: DeviceDescriptor) -> None:
        """Tombstone retained HA metadata and device state after revocation.

        Removing discovery alone hides the entity in HA, but retained state
        would still expose its last metadata to any MQTT broker subscriber.
        """
        self._purge_retained(self._device_tombstone_topics(device))

    def publish_home(
        self, *, home_id: str, name: str, device_count: int, healthy: bool
    ) -> None:
        if not home_id:
            return
        with self._lock:
            previous_home_id = (
                str(self._home["home_id"]) if self._home is not None else None
            )
            started = self._started
            self._home = {
                "home_id": home_id,
                "name": name or "Michi Home",
                "device_count": int(device_count),
                "healthy": bool(healthy),
            }
            home = dict(self._home)
        if started and previous_home_id and previous_home_id != home_id:
            self._remove_home_discovery(previous_home_id)
        if started:
            self._publish_home_discovery(home)
            self._publish_home_state(home)
            self._mark_publish_ok()

    def _home_key(self, home_id: str) -> str:
        digest = hashlib.blake2s(home_id.encode("utf-8"), digest_size=5).hexdigest()
        return f"home_{self._safe_token(home_id)[:32]}_{digest}"

    def _home_topic(self, home_id: str) -> str:
        return (
            f"{self._discovery_prefix}/device/{self._node_id}/"
            f"{self._home_key(home_id)}/config"
        )

    def _home_base(self, home_id: str) -> str:
        return f"michi/{self._node_id}/{self._home_key(home_id)}"

    def _publish_home_discovery(self, home: Mapping[str, Any]) -> None:
        home_id = str(home["home_id"])
        key = self._home_key(home_id)
        base = self._home_base(home_id)
        payload = {
            "device": {
                "identifiers": [f"michi_{key}"],
                "name": str(home.get("name") or "Michi Home"),
                "manufacturer": "Michi",
                "model": "michi_home",
            },
            "origin": self._origin(),
            "components": {
                "devices": {
                    "platform": "sensor",
                    "name": "Dispositivos",
                    "unique_id": f"michi_{key}_devices",
                    "state_topic": f"{base}/state/devices",
                },
                "health": {
                    "platform": "binary_sensor",
                    "name": "Salud",
                    "unique_id": f"michi_{key}_health",
                    "state_topic": f"{base}/state/health",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                },
            },
        }
        self._publish_json(self._home_topic(home_id), payload, retain=True)

    def _publish_home_state(self, home: Mapping[str, Any]) -> None:
        base = self._home_base(str(home["home_id"]))
        self._transport.publish(
            f"{base}/state/devices", str(int(home["device_count"])), retain=True
        )
        self._transport.publish(
            f"{base}/state/health", "ON" if home["healthy"] else "OFF", retain=True
        )

    def _home_tombstone_topics(self, home_id: str) -> tuple[str, ...]:
        base = self._home_base(home_id)
        return (
            self._home_topic(home_id),
            f"{base}/state/devices",
            f"{base}/state/health",
        )

    def _remove_home_discovery(self, home_id: str) -> None:
        self._purge_retained(self._home_tombstone_topics(home_id))

    def clear_home(self) -> None:
        """Remove retained HA Home discovery after Home is removed/restored."""
        with self._lock:
            previous = self._home
            self._home = None
            started = self._started
        if started and previous is not None:
            self._remove_home_discovery(str(previous["home_id"]))

    def handle_command(
        self, canonical_id: str, command: str, value: Any = None
    ) -> None:
        with self._lock:
            device = self._devices.get(canonical_id)
            started = self._started
        if (
            not started
            or device is None
            or not device.home_assistant_allowed
            or DeviceCapability.PLAYBACK_ENDPOINT not in device.capabilities
        ):
            raise HomeAssistantAdapterError("unknown or non-playback Michi endpoint")
        normalized = command.strip().lower()
        if normalized not in _ALLOWED_COMMANDS:
            raise HomeAssistantAdapterError(
                f"unsupported Home Assistant command: {command}"
            )
        if normalized == "volume":
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise HomeAssistantAdapterError("volume must be numeric") from exc
            if not 0 <= numeric <= 100:
                raise HomeAssistantAdapterError("volume must be between 0 and 100")
            value = int(numeric) if numeric.is_integer() else numeric
        elif normalized == "mute":
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "on", "1"}:
                    value = True
                elif lowered in {"false", "off", "0"}:
                    value = False
                else:
                    raise HomeAssistantAdapterError("mute must be boolean")
            elif not isinstance(value, bool):
                raise HomeAssistantAdapterError("mute must be boolean")
        self._command_sink(canonical_id, normalized, value)

    @classmethod
    def _is_secret_key(cls, key: object) -> bool:
        normalized = str(key).strip().lower().replace("-", "_")
        return any(fragment in normalized for fragment in _FORBIDDEN_KEY_FRAGMENTS)

    @classmethod
    def _sanitize_state(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): cls._sanitize_state(item)
                for key, item in value.items()
                if not cls._is_secret_key(key)
            }
        if isinstance(value, (list, tuple)):
            return [cls._sanitize_state(item) for item in value]
        return value

    def _on_birth(self, _topic: str, payload: str) -> None:
        if str(payload).strip().lower() == "online":
            self.republish()

    def _on_message(self, topic: str, payload: str) -> None:
        if not self.started:
            return
        # michi/<node>/<entity-key>/command/<action>
        parts = topic.split("/")
        if (
            len(parts) != 5
            or parts[0] != "michi"
            or parts[1] != self._node_id
            or parts[3] != "command"
        ):
            return
        key, command = parts[2], parts[4].strip().lower()
        with self._lock:
            devices = tuple(self._devices.values())
        device = next(
            (item for item in devices if self._entity_key(item) == key),
            None,
        )
        if device is None:
            return
        value: Any = None
        if command in {"volume", "mute"}:
            value = payload
        # Callback threads must not be killed by an invalid external command.
        try:
            self.handle_command(device.canonical_id, command, value)
        except HomeAssistantAdapterError:
            return

    def _publish_availability(self, device: DeviceDescriptor, online: bool) -> None:
        self._transport.publish(
            f"{self._base(device)}/availability",
            "online" if online else "offline",
            retain=True,
        )

    def _publish_json(
        self, topic: str, payload: dict[str, Any], *, retain: bool
    ) -> None:
        self._transport.publish(
            topic,
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            retain=retain,
        )
