"""External home-automation ports (E11.5-D)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from michi_ecosystem.domain.device_registry import DeviceDescriptor


@dataclass(frozen=True)
class HomeAutomationConfiguration:
    """Non-secret Home Assistant configuration safe to project into QML.

    Broker passwords are intentionally absent.  The settings port accepts a
    write-only password update, but never returns secret material to the core
    or presentation layers.
    """

    broker: str = ""
    port: int = 1883
    tls: bool = False
    username: str = ""
    auto_discovery: bool = True
    publish_devices: bool = True
    diagnostics: bool = True


class HomeAutomationPort(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def republish(self) -> None: ...

    def publish_device(self, device: DeviceDescriptor) -> None: ...

    def publish_state(self, canonical_id: str, state: dict[str, Any]) -> None: ...

    def remove_device(self, canonical_id: str) -> None: ...

    def publish_home(
        self, *, home_id: str, name: str, device_count: int, healthy: bool
    ) -> None: ...

    def clear_home(self) -> None: ...

    def handle_command(
        self, canonical_id: str, command: str, value: Any = None
    ) -> None: ...


class HomeAutomationSettingsPort(Protocol):
    """Optional host-owned secure settings seam.

    Implementations decide where secrets live (desktop keyring, encrypted
    store, etc.).  ``configuration`` MUST return only non-secret fields.
    ``password`` is write-only and ``None`` means preserve the current secret.
    """

    def configuration(self) -> HomeAutomationConfiguration: ...

    def configure(
        self,
        *,
        broker: str,
        port: int,
        tls: bool,
        username: str,
        password: str | None,
        auto_discovery: bool,
        publish_devices: bool,
        diagnostics: bool,
    ) -> None: ...


class MqttTransportPort(Protocol):
    """Tiny MQTT seam; concrete client ownership stays outside the domain."""

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def publish(self, topic: str, payload: str, *, retain: bool = False) -> None: ...

    def subscribe(self, topic: str, callback) -> None: ...


class ObservableMqttTransportPort(Protocol):
    """Optional transport capability: ongoing connectivity events.

    Events are normalized lowercase strings: ``connecting``, ``connected``,
    ``reconnecting``, ``disconnected``, ``error``. A host transport that cannot
    monitor the link simply omits this method; the UI then reports an honest
    ``unknown`` state instead of fabricating "connected" from activation.
    """

    def set_state_callback(self, callback) -> None: ...
