"""E11.6 Player QML read model + safe Space intents."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.capability_resolution import (
    Availability,
    CapabilityDecision,
    CapabilityResolutionService,
    Operation,
)
from michi_ecosystem.application.device_registry_service import DeviceRegistryService
from michi_ecosystem.application.operation_history import OperationHistory
from michi_ecosystem.application.spaces_service import SpaceError, SpacesService

_ERROR_COPY = {
    "HOME_UNAVAILABLE": "Crea o recupera Michi Home para organizar espacios.",
    "OWNER_REQUIRED": "Desbloquea tu cuenta OWNER para gestionar espacios.",
    "INVALID_NAME": "Introduce un nombre de espacio válido de hasta 48 caracteres.",
    "DUPLICATE_NAME": "Ya existe un espacio con ese nombre.",
    "SPACE_UNKNOWN": "El espacio ya no está disponible.",
    "SPACE_LIMIT": "Límite de 64 espacios alcanzado.",
    "DEVICE_NOT_TRUSTED": "Sólo puedes asignar dispositivos activos del Michi Home actual.",
    "SPACE_NOT_EMPTY": "Quita todos los dispositivos del espacio antes de eliminarlo.",
}


class EcosystemOperationsBridge(QObject):
    stateChanged = Signal()
    busyChanged = Signal()
    errorOccurred = Signal(str, str)
    operationFinished = Signal(str, bool)
    _completed = Signal(str, str, bool)
    _refreshRequested = Signal()
    auditWarning = Signal(str)
    navigationRequested = Signal(str)
    streamSelectionRequested = Signal(str)
    _auditFailed = Signal(str)

    def __init__(
        self,
        *,
        dashboard: object,
        registry: DeviceRegistryService,
        spaces: SpacesService | None,
        history: OperationHistory,
        owner_authorized=None,
        adapter_ready: Callable[[object, Operation], bool] | None = None,
        operation_compatibility: Callable[[object, Operation], bool | None]
        | None = None,
        operation_busy: Callable[[], bool] | None = None,
        support_destination: Callable[[], Path | None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._dashboard = dashboard
        self._registry = registry
        self._spaces = spaces
        self._history = history
        self._capabilities = CapabilityResolutionService()
        self._owner_authorized = owner_authorized or (lambda: False)
        self._busy = False
        self._audit_warning = ""
        self._last_error = ""
        self.errorOccurred.connect(
            self._remember_error, Qt.ConnectionType.QueuedConnection
        )
        self._adapter_ready = adapter_ready or (lambda _device, _operation: False)
        self._operation_compatibility = operation_compatibility or (
            lambda _device, _operation: None
        )
        self._operation_busy = operation_busy or (lambda: False)
        self._support_destination = support_destination
        self._discovery = None
        self._auditFailed.connect(
            self._on_audit_failure, Qt.ConnectionType.QueuedConnection
        )
        self._completed.connect(self._on_completed, Qt.ConnectionType.QueuedConnection)
        self._refreshRequested.connect(self.refresh, Qt.ConnectionType.QueuedConnection)

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    def attach_discovery(self, controller: object) -> None:
        """Attach the host discovery controller (manual start/stop only)."""
        self._discovery = controller
        self.stateChanged.emit()

    def _discovery_value(self, name: str, default):
        if self._discovery is None:
            return default
        try:
            return getattr(self._discovery, name)
        except Exception:
            return default

    @Property(bool, notify=stateChanged)
    def discoveryAvailable(self) -> bool:
        return bool(self._discovery_value("available", False))

    @Property(bool, notify=stateChanged)
    def discoveryRunning(self) -> bool:
        return bool(self._discovery_value("running", False))

    @Property(str, notify=stateChanged)
    def discoveryState(self) -> str:
        return str(self._discovery_value("state", "unavailable"))

    @Property("QVariantMap", notify=stateChanged)
    def discoveryHealth(self) -> dict[str, Any]:
        health = self._discovery_value("health", {})
        return dict(health) if isinstance(health, dict) else {}

    @Slot()
    def startDiscovery(self) -> None:
        if self._discovery is None:
            self.errorOccurred.emit(
                "DISCOVERY_UNAVAILABLE",
                "El descubrimiento no está disponible en este host.",
            )
            return
        try:
            self._discovery.start()
        except Exception:
            self.errorOccurred.emit(
                "DISCOVERY_START_FAILED",
                "No se pudo iniciar el descubrimiento.",
            )
        self.stateChanged.emit()

    @Slot()
    def stopDiscovery(self) -> None:
        if self._discovery is None:
            return
        try:
            self._discovery.stop()
        except Exception:
            self.errorOccurred.emit(
                "DISCOVERY_STOP_FAILED",
                "No se pudo detener el descubrimiento.",
            )
        self.stateChanged.emit()

    @Property(bool, notify=stateChanged)
    def spacesAvailable(self) -> bool:
        return self._spaces is not None and self._spaces.home_available

    @Property(bool, notify=stateChanged)
    def ownerAuthorized(self) -> bool:
        return bool(self._owner_authorized())

    @Property("QVariantMap", notify=stateChanged)
    def doctor(self) -> dict[str, Any]:
        return dict(self._dashboard.dashboard_snapshot().get("doctor") or {})

    @Property("QVariantList", notify=stateChanged)
    def issues(self) -> list[dict[str, Any]]:
        return list(self.doctor.get("issues") or [])

    @Property("QVariantList", notify=stateChanged)
    def spaces(self) -> list[dict[str, Any]]:
        if self._spaces is None:
            return []
        try:
            spaces = []
            for space in self._spaces.list_spaces():
                entry = space.projection()
                entry["members"] = [
                    {
                        "id": canonical_id,
                        "name": (
                            device.name
                            if (device := self._registry.get(canonical_id))
                            else "Dispositivo desconocido"
                        ),
                    }
                    for canonical_id in space.devices
                ]
                spaces.append(entry)
            return spaces
        except SpaceError:
            return []

    @Property(bool, notify=stateChanged)
    def supportExportAvailable(self) -> bool:
        return self._support_destination is not None

    @Property(str, notify=stateChanged)
    def auditWarningText(self) -> str:
        return self._audit_warning

    @Property(str, notify=stateChanged)
    def lastErrorText(self) -> str:
        return self._last_error

    @Slot(str, str)
    def _remember_error(self, _code: str, message: str) -> None:
        self._last_error = message
        self.stateChanged.emit()

    @Property("QVariantList", notify=stateChanged)
    def events(self) -> list[dict[str, Any]]:
        return [ev.projection() for ev in self._history.list()]

    def _decision(self, device, op: Operation) -> CapabilityDecision:
        try:
            return self._capabilities.resolve(
                device,
                op,
                adapter_available=bool(self._adapter_ready(device, op)),
                owner_authorized=bool(self._owner_authorized()),
                compatible=self._operation_compatibility(device, op),
                busy=bool(self._operation_busy()),
            )
        except Exception:
            # QML getters must never propagate adapter/configuration exceptions.
            # An unknown status cannot be portrayed as READY.
            return CapabilityDecision(
                op,
                Availability.UNAVAILABLE,
                "No se pudo verificar la disponibilidad del host.",
            )

    @Property("QVariantList", notify=stateChanged)
    def devices(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for device in self._registry.list_devices():
            actions = [self._decision(device, op).projection() for op in Operation]
            result.append(
                {
                    "id": device.canonical_id,
                    "name": device.name,
                    "type": device.type.value,
                    "online": device.online,
                    "homeId": device.michi_home_id or "",
                    "trusted": device.trusted_home_member,
                    "detailAvailable": device.type.value
                    in ("music_stream", "micro_server", "mobile"),
                    "actions": actions,
                }
            )
        return result

    @Slot()
    def refresh(self) -> None:
        self.stateChanged.emit()

    def on_registry_changed(self, _devices) -> None:
        self._refreshRequested.emit()

    def _mutate(self, code: str, action) -> None:
        if self._busy:
            self.errorOccurred.emit("BUSY", "Ya existe una operación en curso.")
            return
        if self._spaces is None:
            self.errorOccurred.emit("HOME_UNAVAILABLE", _ERROR_COPY["HOME_UNAVAILABLE"])
            return
        self._busy = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                action()
            except SpaceError as exc:
                self._completed.emit(code, exc.code, False)
                return
            except Exception:
                self._completed.emit(code, "OPERATION_FAILED", False)
                return
            # The primary operation is committed. An audit-store outage must
            # never turn that successful mutation into a false failure.
            try:
                self._history.record(code)
            except Exception:
                self._auditFailed.emit("HISTORY_UNAVAILABLE")
            self._completed.emit(code, "", True)

        try:
            threading.Thread(
                target=work, name="michi-ecosystem-spaces", daemon=True
            ).start()
        except Exception:
            self._busy = False
            self.busyChanged.emit()
            self.errorOccurred.emit(
                "OPERATION_FAILED", "No se pudo iniciar la operación."
            )

    @Slot(str, str, bool)
    def _on_completed(self, code: str, err: str, success: bool) -> None:
        self._busy = False
        self.busyChanged.emit()
        if success:
            self._last_error = ""
        self.stateChanged.emit()
        if not success:
            text = (
                "No fue posible exportar el informe de soporte."
                if err == "EXPORT_FAILED"
                else _ERROR_COPY.get(err, "No se pudo completar la operación.")
            )
            self.errorOccurred.emit(err, text)
        self.operationFinished.emit(code, success)

    @Slot(str)
    def createSpace(self, name: str) -> None:
        self._mutate("SPACE_CREATED", lambda: self._spaces.create(name))

    @Slot(str, str)
    def renameSpace(self, space_id: str, name: str) -> None:
        self._mutate("SPACE_RENAMED", lambda: self._spaces.rename(space_id, name))

    @Slot(str)
    def deleteSpace(self, space_id: str) -> None:
        self._mutate("SPACE_REMOVED", lambda: self._spaces.remove(space_id))

    @Slot(str, str)
    def assignDevice(self, space_id: str, canonical_id: str) -> None:
        self._mutate(
            "SPACE_ASSIGNED", lambda: self._spaces.assign(space_id, canonical_id)
        )

    @Slot(str, str)
    def unassignDevice(self, space_id: str, canonical_id: str) -> None:
        self._mutate(
            "SPACE_UNASSIGNED", lambda: self._spaces.unassign(space_id, canonical_id)
        )

    @Slot(str)
    def _on_audit_failure(self, _code: str) -> None:
        self._audit_warning = "No se pudo registrar el evento. La operación principal sigue siendo válida."
        self.auditWarning.emit(self._audit_warning)
        self.stateChanged.emit()

    def _record_navigation(self, event: str) -> None:
        try:
            self._history.record(event)
        except Exception:
            self._on_audit_failure("HISTORY_UNAVAILABLE")
        self.stateChanged.emit()

    @Slot()
    def viewDiagnostics(self) -> None:
        self._record_navigation("DIAGNOSTICS_VIEWED")

    @Slot(str)
    def openDevice(self, canonical_id: str) -> None:
        device = self._registry.get(canonical_id)
        if device is None:
            self.errorOccurred.emit("DEVICE_NOT_FOUND", "Dispositivo no disponible.")
            return
        from michi_ecosystem.domain.device_registry import DeviceType

        routes = {
            DeviceType.MUSIC_STREAM: "ecosystem/streams",
            DeviceType.MICRO_SERVER: "ecosystem/micro-server",
            DeviceType.MOBILE: "ecosystem/mobile",
            DeviceType.BIG_SERVER: "ecosystem/devices",
        }
        route = routes.get(device.type)
        if not route or route == "ecosystem/devices":
            self.errorOccurred.emit(
                "DETAIL_UNAVAILABLE",
                "La gestión de este dispositivo todavía no está disponible en Ecosystem.",
            )
            return
        if device.type is DeviceType.MUSIC_STREAM:
            self.streamSelectionRequested.emit(canonical_id)
        self._record_navigation("DEVICE_DETAIL_OPENED")
        self.navigationRequested.emit(route)

    @Slot(str, str)
    def openDeviceAction(self, canonical_id: str, action: str) -> None:
        device = self._registry.get(canonical_id)
        try:
            operation = Operation(action)
        except ValueError:
            self.errorOccurred.emit("ACTION_UNSUPPORTED", "Acción desconocida.")
            return
        if device is None:
            self.errorOccurred.emit("DEVICE_NOT_FOUND", "Dispositivo no disponible.")
            return
        decision = self._decision(device, operation)
        if decision.status is not Availability.READY:
            self.errorOccurred.emit("ACTION_UNAVAILABLE", decision.reason)
            return
        # Navigation-only. Destructive/remote commands are re-authorized by
        # their real owner. The Devices content path must not execute AirCat.
        if operation in {
            Operation.DIAGNOSTICS,
            Operation.FIRMWARE_UPDATE,
            Operation.NETWORK_REPROVISION,
        }:
            self.openDevice(canonical_id)
        elif operation is Operation.CONTENT_SYNC:
            self.navigationRequested.emit(
                "devices/mobile" if device.type.value == "mobile" else "devices"
            )
        else:
            self.errorOccurred.emit(
                "ACTION_UNAVAILABLE", "Utiliza Michi Control en NowPlayingBar."
            )

    @Slot()
    def exportSupport(self) -> None:
        if self._support_destination is None:
            self.errorOccurred.emit(
                "EXPORT_UNAVAILABLE",
                "El Player no tiene un selector de destino configurado.",
            )
            return
        if self._busy:
            self.errorOccurred.emit("BUSY", "Ya existe una operación en curso.")
            return
        try:
            destination = self._support_destination()
            if destination is None:
                return  # User cancelled the file chooser.
        except Exception:
            self.errorOccurred.emit(
                "EXPORT_FAILED", "No se pudo obtener el destino de exportación."
            )
            return
        self._busy = True
        self.busyChanged.emit()
        doctor = self.doctor

        def work() -> None:
            try:
                self._history.export_support_bundle(Path(destination), doctor=doctor)
            except Exception:
                self._completed.emit("SUPPORT_EXPORTED", "EXPORT_FAILED", False)
                return
            try:
                self._history.record("SUPPORT_EXPORTED")
            except Exception:
                self._auditFailed.emit("HISTORY_UNAVAILABLE")
            self._completed.emit("SUPPORT_EXPORTED", "", True)

        try:
            threading.Thread(
                target=work, name="michi-ecosystem-support", daemon=True
            ).start()
        except Exception:
            self._busy = False
            self.busyChanged.emit()
            self.errorOccurred.emit(
                "EXPORT_FAILED", "No se pudo iniciar la exportación."
            )
