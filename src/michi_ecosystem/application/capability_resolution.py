"""E11.6: honest operation availability, not an execution authority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from michi_ecosystem.domain.device_registry import (
    DeviceCapability,
    DeviceDescriptor,
    DeviceType,
    HomeMembershipState,
)


class Operation(StrEnum):
    DIAGNOSTICS = "diagnostics"
    FIRMWARE_UPDATE = "firmware_update"
    NETWORK_REPROVISION = "network_reprovision"
    CONTENT_SYNC = "content_sync"
    PLAYBACK_TARGET = "playback_target"
    FACTORY_RECREATE = "factory_recreate"


class Availability(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    BUSY = "busy"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"


_REQUIRED = {
    Operation.DIAGNOSTICS: DeviceCapability.DIAGNOSTICS,
    Operation.FIRMWARE_UPDATE: DeviceCapability.FIRMWARE_UPDATE,
    Operation.NETWORK_REPROVISION: DeviceCapability.NETWORK_REPROVISION,
    Operation.CONTENT_SYNC: DeviceCapability.CONTENT_SYNC,
    Operation.PLAYBACK_TARGET: DeviceCapability.PLAYBACK_ENDPOINT,
    Operation.FACTORY_RECREATE: DeviceCapability.FACTORY_RECREATE,
}


@dataclass(frozen=True)
class CapabilityDecision:
    operation: Operation
    status: Availability
    reason: str

    @property
    def enabled(self) -> bool:
        return self.status is Availability.READY

    def projection(self) -> dict[str, str | bool]:
        return {
            "action": self.operation.value,
            "status": self.status.value,
            "reason": self.reason,
            "enabled": self.enabled,
        }


class CapabilityResolutionService:
    """Evaluate read-model evidence and host readiness; never issue commands."""

    def resolve(
        self,
        device: DeviceDescriptor,
        operation: Operation,
        *,
        adapter_available: bool = False,
        owner_authorized: bool = False,
        busy: bool = False,
        compatible: bool | None = None,
    ) -> CapabilityDecision:
        def result(state: Availability, reason: str) -> CapabilityDecision:
            return CapabilityDecision(operation, state, reason)

        if operation is Operation.FACTORY_RECREATE:
            return result(
                Availability.BLOCKED, "Usa el flujo protegido de Factory/Recreate."
            )
        # A generic DAP is a local USB storage target, not a Michi Mobile
        # CONTENT_SYNC/AirCat endpoint. Keep the decision consistent with
        # DeviceDescriptor.sync_allowed and the Michi Devices ownership boundary.
        required = (
            DeviceCapability.STORAGE_TARGET
            if operation is Operation.CONTENT_SYNC
            and device.type is DeviceType.GENERIC_DAP
            else _REQUIRED[operation]
        )
        if required not in device.capabilities:
            return result(
                Availability.UNSUPPORTED, "El dispositivo no declara esta capacidad."
            )
        if compatible is False:
            return result(Availability.BLOCKED, "Contrato o versión incompatible.")
        if compatible is None and operation in {
            Operation.FIRMWARE_UPDATE,
            Operation.NETWORK_REPROVISION,
        }:
            return result(
                Availability.BLOCKED, "Compatibilidad de firmware no verificada."
            )
        if operation is Operation.CONTENT_SYNC:
            if device.type not in {DeviceType.MOBILE, DeviceType.GENERIC_DAP}:
                return result(
                    Availability.UNSUPPORTED,
                    "La sincronización pertenece a Michi Devices.",
                )
            if not device.sync_allowed:
                return result(
                    Availability.BLOCKED, "Sin membresía o capacidad de sincronización."
                )
            if device.type is DeviceType.GENERIC_DAP and not any(
                t.value == "usb" for t in device.transports
            ):
                return result(Availability.UNAVAILABLE, "Conecta el DAP por USB.")
        elif (
            device.type is not DeviceType.DESKTOP_PLAYER
            and device.home_membership is not HomeMembershipState.ACTIVE
        ):
            return result(
                Availability.BLOCKED, "El dispositivo no está activo en Michi Home."
            )
        if (
            operation in {Operation.FIRMWARE_UPDATE, Operation.NETWORK_REPROVISION}
            and not owner_authorized
        ):
            return result(Availability.BLOCKED, "Requiere una sesión OWNER autorizada.")
        if busy:
            return result(Availability.BUSY, "Existe otra operación en curso.")
        if not device.online and not (
            operation is Operation.CONTENT_SYNC
            and device.type is DeviceType.GENERIC_DAP
        ):
            return result(
                Availability.UNAVAILABLE, "Dispositivo sin conexión confirmada."
            )
        if not adapter_available:
            return result(
                Availability.UNAVAILABLE,
                "El host todavía no proporciona esta operación.",
            )
        return result(
            Availability.READY, "Operación disponible mediante el host autorizado."
        )
