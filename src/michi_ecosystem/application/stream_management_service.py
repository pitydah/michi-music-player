"""Management plane for already-created Music Streams (E11.5-C/Lifecycle).

Creation and Factory Recreate remain owned by the factory workflow.  This
service handles the normal lifecycle of a provisioned Stream and derives UI
actions exclusively from Device Registry capabilities.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from michi_ecosystem.application.device_registry_service import DeviceRegistryService
from michi_ecosystem.domain.device_registry import (
    DeviceCapability,
    DeviceDescriptor,
    DeviceType,
)
from michi_ecosystem.ports.stream import StreamManagementCommandPort


class StreamManagementError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class StreamAction(StrEnum):
    DIAGNOSTICS = "diagnostics"
    FIRMWARE_UPDATE = "firmware_update"
    NETWORK_REPROVISION = "network_reprovision"
    FACTORY_RECREATE = "factory_recreate"


@dataclass(frozen=True)
class StreamActionAvailability:
    action: StreamAction
    enabled: bool
    reason: str = ""


_CAPABILITY_FOR_ACTION = {
    StreamAction.DIAGNOSTICS: DeviceCapability.DIAGNOSTICS,
    StreamAction.FIRMWARE_UPDATE: DeviceCapability.FIRMWARE_UPDATE,
    StreamAction.NETWORK_REPROVISION: DeviceCapability.NETWORK_REPROVISION,
    StreamAction.FACTORY_RECREATE: DeviceCapability.FACTORY_RECREATE,
}


class StreamManagementService:
    def __init__(
        self,
        registry: DeviceRegistryService,
        *,
        commands: StreamManagementCommandPort | None = None,
        privileged_authorizer: Callable[[], bool] | None = None,
    ) -> None:
        self._registry = registry
        self._commands = commands
        self._privileged_authorizer = privileged_authorizer

    @property
    def commands_available(self) -> bool:
        """True only when the host supplied a real stream command port."""
        return self._commands is not None

    def list_streams(self) -> tuple[DeviceDescriptor, ...]:
        return self._registry.by_type(DeviceType.MUSIC_STREAM)

    def get_stream(self, canonical_id: str) -> DeviceDescriptor:
        device = self._registry.get(canonical_id)
        if device is None or device.type is not DeviceType.MUSIC_STREAM:
            raise StreamManagementError(
                "STREAM_NOT_FOUND", "Music Stream no encontrado"
            )
        return device

    def actions(self, canonical_id: str) -> tuple[StreamActionAvailability, ...]:
        device = self.get_stream(canonical_id)
        result: list[StreamActionAvailability] = []
        for action in StreamAction:
            capability = _CAPABILITY_FOR_ACTION[action]
            supported = capability in device.capabilities
            if not supported:
                result.append(
                    StreamActionAvailability(
                        action, False, "No soportado por este dispositivo"
                    )
                )
            elif (
                action
                in {
                    StreamAction.FIRMWARE_UPDATE,
                    StreamAction.NETWORK_REPROVISION,
                }
                and self._privileged_authorizer is not None
                and not self._privileged_authorizer()
            ):
                result.append(
                    StreamActionAvailability(
                        action, False, "Desbloquea la cuenta OWNER"
                    )
                )
            elif (
                action
                in {
                    StreamAction.DIAGNOSTICS,
                    StreamAction.FIRMWARE_UPDATE,
                    StreamAction.NETWORK_REPROVISION,
                }
                and self._commands is None
            ):
                result.append(
                    StreamActionAvailability(
                        action, False, "Adaptador de gestión no configurado"
                    )
                )
            elif (
                action
                in {
                    StreamAction.DIAGNOSTICS,
                    StreamAction.FIRMWARE_UPDATE,
                    StreamAction.NETWORK_REPROVISION,
                }
                and not device.trusted_home_member
            ):
                result.append(
                    StreamActionAvailability(
                        action,
                        False,
                        "El dispositivo debe ser miembro activo de Michi Home",
                    )
                )
            elif (
                action
                in {
                    StreamAction.DIAGNOSTICS,
                    StreamAction.FIRMWARE_UPDATE,
                    StreamAction.NETWORK_REPROVISION,
                }
                and not device.online
            ):
                result.append(
                    StreamActionAvailability(
                        action, False, "El dispositivo está sin conexión"
                    )
                )
            else:
                # Factory Recreate is deliberately different: it is a local
                # USB recovery path and remains available for revoked/untrusted
                # devices when the capability exists.
                result.append(StreamActionAvailability(action, True))
        return tuple(result)

    def detail(self, canonical_id: str) -> dict[str, Any]:
        device = self.get_stream(canonical_id)
        return {
            "canonicalId": device.canonical_id,
            "michiId": device.michi_id or "",
            "name": device.name,
            "online": device.online,
            "homeMembership": device.home_membership.value,
            "version": device.app_or_firmware_version or "",
            "lastSeenMs": device.last_seen_ms
            if device.last_seen_ms is not None
            else -1,
            "transports": sorted(item.value for item in device.transports),
            "capabilities": sorted(item.value for item in device.capabilities),
            "actions": [
                {
                    "id": availability.action.value,
                    "enabled": availability.enabled,
                    "reason": availability.reason,
                }
                for availability in self.actions(canonical_id)
            ],
        }

    def run_diagnostics(self, canonical_id: str) -> dict[str, Any]:
        self._require_action(canonical_id, StreamAction.DIAGNOSTICS)
        if self._commands is None:
            raise StreamManagementError(
                "COMMAND_PORT_UNAVAILABLE", "diagnóstico no disponible en este host"
            )
        return self._commands.diagnostics(canonical_id)

    def request_firmware_update(self, canonical_id: str) -> None:
        self._require_action(canonical_id, StreamAction.FIRMWARE_UPDATE)
        if self._commands is None:
            raise StreamManagementError(
                "COMMAND_PORT_UNAVAILABLE", "actualización no disponible en este host"
            )
        self._commands.request_firmware_update(canonical_id)

    def reprovision_network(self, canonical_id: str) -> None:
        self._require_action(canonical_id, StreamAction.NETWORK_REPROVISION)
        if self._commands is None:
            raise StreamManagementError(
                "COMMAND_PORT_UNAVAILABLE",
                "configuración de red no disponible en este host",
            )
        self._commands.reprovision_network(canonical_id)

    def _require_action(self, canonical_id: str, action: StreamAction) -> None:
        availability = next(
            item for item in self.actions(canonical_id) if item.action is action
        )
        if not availability.enabled:
            raise StreamManagementError("ACTION_UNAVAILABLE", availability.reason)
