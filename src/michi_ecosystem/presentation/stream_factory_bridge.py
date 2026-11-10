"""Stream Factory bridge (A2/A3/E5/E6): wizard state and async orchestration.

- Worker events reach QML ONLY through Qt queued signals: QObject state is
  mutated on its owning thread (A2).
- Device scanning runs off the GUI thread (A3).
- Firmware acquisition states are surfaced honestly (E5/E6).
- Credentials never become QML properties; flashing runs in the coordinator
  worker; developer mode is explicit (never product).
"""

from __future__ import annotations

import threading
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.factory_coordinator import (
    FactoryEvent,
    FactoryOperationCoordinator,
    FactoryRequest,
    FactoryResult,
)
from michi_ecosystem.application.stream_factory_orchestrator import (
    StreamFactoryOrchestrator,
)
from michi_ecosystem.application.stream_factory_service import (
    FactoryError,
    StreamFactoryService,
)
from michi_ecosystem.domain.flashing import CreationMode, ProvisioningRequest

_ERROR_UX = {
    "OFFICIAL_FIRMWARE_UNAVAILABLE": (
        "Firmware oficial no disponible",
        "Publicá un release oficial en el canal estable o usa modo "
        "desarrollador con un firmware local.",
    ),
    "AUTHENTICITY_NOT_CONFIGURED": (
        "Firma de firmware no configurada",
        "Configura la verificación de autenticidad antes de flashear producción.",
    ),
    "APPROVAL_INVALIDATED": (
        "La aprobación dejó de ser válida",
        "El dispositivo o el firmware cambiaron; revisa y aprobá de nuevo.",
    ),
    "APPROVAL_INVALIDATED_DEVICE": (
        "La placa cambió",
        "La placa presente no es la aprobada; revisa el dispositivo y vuelve a empezar.",
    ),
    "INSTALLATION_CHANGED": (
        "El estado del dispositivo cambió",
        "La placa ya no está vacía o cambió durante la preparación. No se "
        "borró nada; revisa el dispositivo.",
    ),
    "UPDATE_POLICY_MISSING": (
        "Actualización no permitida",
        "Este firmware no declara una política de actualización compatible.",
    ),
    "FACTORY_BLOB_TOO_LARGE": (
        "Configuración Wi-Fi demasiado grande",
        "Acortá el nombre de red o la contraseña.",
    ),
    "RESET_FAILED": (
        "No se pudo reiniciar el dispositivo",
        "Desconectá y reconecta el dispositivo, y reintenta.",
    ),
    "FLASH_VERIFY_MISMATCH": (
        "La verificación de escritura falló",
        "El contenido escrito no coincide con el firmware; reintenta el flasheo.",
    ),
    "RECREATE_OLD_DEVICE_REQUIRED": (
        "Elige el dispositivo a reemplazar",
        "Selecciona un Music Stream activo de tu Home en la revisión.",
    ),
    "FACTORY_RECREATE_REQUIRES_HOME": (
        "Michi Home requerido",
        "Crea o restaura tu Michi Home antes de reconstruir un dispositivo.",
    ),
    "HOME_REQUIRED": (
        "Michi Home requerido",
        "Esta operación necesita un Home configurado y desbloqueado.",
    ),
    "HOME_LOCKED": (
        "Michi Home bloqueado",
        "Desbloquea tu Michi Home para continuar.",
    ),
    "ARTIFACT_ERROR": (
        "El firmware no se pudo preparar",
        "El archivo o referencia del firmware no es utilizable; revisa la "
        "selección e intentá de nuevo.",
    ),
    "DEV_MODE_REQUIRED": (
        "Modo desarrollador requerido",
        "Este firmware es de desarrollo: activa el modo desarrollador de "
        "forma explícita.",
    ),
    "HOME_BOOTSTRAP_TRANSPORT_UNAVAILABLE": (
        "Bootstrap Home no disponible",
        "MICHI-F1 v1 solo transporta la red Wi-Fi. Para crear o recrear un "
        "Music Stream con Home se requiere un bootstrap autenticado con "
        "identidad y membresía (STREAM-REQ-007). Actualiza el firmware de "
        "fábrica cuando esté disponible.",
    ),
    "FACTORY_RECREATE_UNAVAILABLE": (
        "Recreación no disponible",
        "Este entorno no puede reconstruir dispositivos; abre Ecosystem "
        "desde la aplicación completa.",
    ),
    "INVALID_MODE": (
        "Operación no válida",
        "Elige una operación válida (crear, actualizar o recrear).",
    ),
    "OPERATION_BUSY": (
        "Ya hay una operación en curso",
        "Espera a que termine la operación actual.",
    ),
    "PREFLIGHT_BLOCKED": (
        "Revisión previa bloqueada",
        "El dispositivo no pasó la revisión (vacío, modelo o particiones); "
        "revisa el detalle e intentá de nuevo.",
    ),
    "PROVISIONING_ERROR": (
        "Datos de configuración inválidos",
        "Revisa el nombre de red y la contraseña de Wi-Fi.",
    ),
    "UPDATE_PROVISIONING_FORBIDDEN": (
        "Actualización sin tocar la configuración",
        "La actualización preserva Wi-Fi e identidad; no incluye datos de "
        "aprovisionamiento.",
    ),
    "HOME_BUSY": (
        "Home en uso",
        "Hay una creación o restauración de Home en curso; espera a que termine.",
    ),
    "RECOVERY_REQUIRED": (
        "Reconstrucción pendiente de decisión",
        "Hubo un corte durante el flasheo; revisa el estado del dispositivo "
        "en tu Home antes de reintentar.",
    ),
}

STEPS = (
    "intro",
    "device",
    "profile",
    "identity",
    "wifi",
    "firmware",
    "review",
    "flashing",
    "discovery",
    "ready",
)

_STEP_SEQUENCES = {
    CreationMode.CREATE_NEW: STEPS,
    CreationMode.FACTORY_RECREATE: STEPS,
    CreationMode.UPDATE_EXISTING: (
        "intro",
        "device",
        "profile",
        "firmware",
        "review",
        "flashing",
        "discovery",
        "ready",
    ),
}

_FIRMWARE_PHASE_TEXT = {
    "resolving_firmware": "Buscando firmware oficial…",
    "downloading_firmware": "Preparando firmware oficial…",
    "verifying_firmware": "Verificando firmware…",
}


class StreamFactoryBridge(QObject):
    stateChanged = Signal()
    progressChanged = Signal(str)
    finished = Signal(bool, str)
    coordinatorEventReceived = Signal(object)
    coordinatorFinishedReceived = Signal(object)
    devicesScanFinished = Signal(object)

    def __init__(
        self,
        service: StreamFactoryService,
        *,
        board: str = "waveshare-esp32s3-lcd-2",
        firmware_reference: str = "",
        developer_mode: bool = False,
        allow_partial_home_bootstrap: bool | None = None,
        acquisition=None,
        firmware_selection: str = "official_recommended",
        enrollment=None,
        home_provider=None,
        recreate=None,
        old_device_provider=None,
        recreate_devices_provider=None,
        home_access_provider=None,
        home_lease_provider=None,
        orchestrator=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._board = board
        self._firmware_reference = firmware_reference
        self._step_index = 0
        self._devices: list[dict] = []
        self._selected_port = ""
        self._mode = CreationMode.CREATE_NEW
        self._device_name = ""
        self._region = ""
        self._ssid = ""
        self._password = ""  # transient; never a QML property
        self._factory_confirmed = False
        self._busy = False
        self._scanning = False
        self._stage = ""
        self._phase = ""
        self._progress_determinate = False
        self._progress_fraction: float | None = None
        self._cancel_status = ""
        self._error = ""
        self._last_error_code = ""
        self._flash_status = ""
        self._network_status = ""
        self._home_status = ""
        self._firmware_selection = firmware_selection
        self._recreate_status = ""
        self._recreate_tx_id = ""
        self._recreate_old_device = ""
        self._recreate_devices_provider = recreate_devices_provider
        self._coordinator = FactoryOperationCoordinator(
            service,
            on_event=lambda event: self.coordinatorEventReceived.emit(event),
            on_finished=lambda result: self.coordinatorFinishedReceived.emit(result),
            acquisition=acquisition,
            developer_mode=developer_mode,
        )
        self.coordinatorEventReceived.connect(
            self._on_event, Qt.ConnectionType.QueuedConnection
        )
        self.coordinatorFinishedReceived.connect(
            self._on_finished, Qt.ConnectionType.QueuedConnection
        )
        self.devicesScanFinished.connect(
            self._on_devices_scanned, Qt.ConnectionType.QueuedConnection
        )
        self._orchestrator = orchestrator or StreamFactoryOrchestrator(
            coordinator=self._coordinator,
            enrollment=enrollment,
            home_provider=home_provider,
            recreate=recreate,
            old_device_provider=old_device_provider
            or (lambda: self._recreate_old_device or None),
            home_access_provider=home_access_provider,
            home_lease_provider=home_lease_provider,
            # Product mode blocks the partial v1 Home bootstrap (I2); an
            # explicit lab flag (or developer mode) keeps the simulated flow.
            allow_partial_home_bootstrap=(
                developer_mode
                if allow_partial_home_bootstrap is None
                else allow_partial_home_bootstrap
            ),
        )

    # ── properties (no credentials) ─────────────────────────────────────

    def _sequence(self) -> tuple[str, ...]:
        return _STEP_SEQUENCES[self._mode]

    @property
    def orchestrator(self):
        """Exposed for explicit ownership by the composition root (E)."""
        return self._orchestrator

    @Property(str, notify=stateChanged)
    def step(self) -> str:
        sequence = self._sequence()
        return sequence[min(self._step_index, len(sequence) - 1)]

    @Property(int, notify=stateChanged)
    def stepIndex(self) -> int:
        return self._step_index

    @Property(int, notify=stateChanged)
    def stepCount(self) -> int:
        return len(self._sequence())

    @Property("QVariantList", notify=stateChanged)
    def devices(self) -> list[dict]:
        return self._devices

    @Property(bool, notify=stateChanged)
    def scanning(self) -> bool:
        return self._scanning

    @Property(str, notify=stateChanged)
    def selectedPort(self) -> str:
        return self._selected_port

    @Property(str, notify=stateChanged)
    def mode(self) -> str:
        return self._mode.value

    @Property(str, notify=stateChanged)
    def board(self) -> str:
        return self._board

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def progressStage(self) -> str:
        return self._stage or self._phase

    @Property(bool, notify=stateChanged)
    def progressDeterminate(self) -> bool:
        # Determinate ONLY for real byte downloads (A5); flash stays
        # indeterminate until a backend reports real progress.
        return self._progress_determinate

    @Property(float, notify=stateChanged)
    def progressFraction(self) -> float:
        return -1.0 if self._progress_fraction is None else self._progress_fraction

    @Property(str, notify=stateChanged)
    def cancelStatus(self) -> str:
        return self._cancel_status

    @Property(str, notify=stateChanged)
    def firmwareState(self) -> str:
        if self._last_error_code == "OFFICIAL_FIRMWARE_UNAVAILABLE":
            return "No hay firmware oficial disponible todavía."
        if self._last_error_code == "AUTHENTICITY_NOT_CONFIGURED":
            return "Falta la verificación de autenticidad del firmware."
        return _FIRMWARE_PHASE_TEXT.get(self._phase, "")

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error

    @Property(str, notify=stateChanged)
    def flashStatus(self) -> str:
        return self._flash_status

    @Property(str, notify=stateChanged)
    def networkStatus(self) -> str:
        return self._network_status

    @Property(str, notify=stateChanged)
    def homeStatus(self) -> str:
        return self._home_status

    @Property(bool, notify=stateChanged)
    def canStartFlash(self) -> bool:
        if self._busy or not self._selected_port:
            return False
        needs_network = self._mode is not CreationMode.UPDATE_EXISTING
        if needs_network and not self._ssid:
            return False
        if self._mode is CreationMode.FACTORY_RECREATE:
            # B3: a recreate requires the selected old device AND the
            # explicit destructive confirmation.
            return self._factory_confirmed and bool(self._recreate_old_device)
        return True

    @Property(str, notify=stateChanged)
    def errorTitle(self) -> str:
        entry = _ERROR_UX.get(self._last_error_code)
        return entry[0] if entry else ""

    @Property(str, notify=stateChanged)
    def errorHelp(self) -> str:
        entry = _ERROR_UX.get(self._last_error_code)
        return entry[1] if entry else ""

    @Property("QVariantList", notify=stateChanged)
    def reviewRows(self) -> list[dict]:
        operation = {
            CreationMode.CREATE_NEW: "Crear nuevo Music Stream",
            CreationMode.UPDATE_EXISTING: "Actualizar firmware",
            CreationMode.FACTORY_RECREATE: "Recrear configuración",
        }[self._mode]
        rows = [
            {"label": "Dispositivo USB", "value": self._selected_port or "—"},
            {"label": "Operación", "value": operation},
        ]
        if self._mode is CreationMode.FACTORY_RECREATE:
            rows.append(
                {
                    "label": "Dispositivo reemplazado",
                    "value": self.recreateDeviceName or "—",
                }
            )
        if self._mode is not CreationMode.UPDATE_EXISTING:
            rows.append({"label": "Red Wi-Fi", "value": self._ssid or "—"})
        rows.append(
            {
                "label": "Firmware",
                "value": self._firmware_reference
                or (
                    "oficial recomendado"
                    if self._firmware_selection == "official_recommended"
                    else "—"
                ),
            }
        )
        return rows

    @Property("QVariantList", notify=stateChanged)
    def reviewAdvancedRows(self) -> list[dict]:
        return [
            {"label": "Puerto", "value": self._selected_port or "—"},
            {"label": "Placa", "value": self._board},
            {"label": "Referencia", "value": self._firmware_reference or "—"},
        ]

    @Property(str, notify=stateChanged)
    def reviewSummary(self) -> str:
        lines = [
            f"Puerto: {self._selected_port or '—'}",
            f"Placa: {self._board}",
            f"Modo: {self._mode.value}",
        ]
        if self._mode is CreationMode.FACTORY_RECREATE:
            lines.append(f"Reemplaza: {self.recreateDeviceName or '—'}")
        if self._mode is not CreationMode.UPDATE_EXISTING:
            lines.append(f"Red: {self._ssid or '—'}")
        lines.append(f"Firmware: {self._firmware_reference or '—'}")
        return "\n".join(lines)

    # ── slots ───────────────────────────────────────────────────────────

    @Slot()
    def scanDevices(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._emit()
        thread = threading.Thread(target=self._run_scan, daemon=True)
        thread.start()

    def _run_scan(self) -> None:
        try:
            devices = [
                asdict(candidate) for candidate in self._service.detect_devices()
            ]
        except Exception:
            devices = []
        self.devicesScanFinished.emit(devices)

    @Slot(object)
    def _on_devices_scanned(self, devices: object) -> None:
        self._devices = list(devices)  # type: ignore[arg-type]
        self._scanning = False
        self._emit()

    @Slot(str)
    def selectDevice(self, port: str) -> None:
        self._selected_port = port
        self._emit()

    @Slot(str)
    def selectMode(self, mode: str) -> None:
        try:
            self._mode = CreationMode(mode)
        except ValueError:
            return
        if self._mode is not CreationMode.FACTORY_RECREATE:
            self._factory_confirmed = False
        self._step_index = min(self._step_index, len(self._sequence()) - 1)
        self._emit()
        if self._mode is not CreationMode.FACTORY_RECREATE:
            # P1: leaving the mode invalidates any stale recreate selection.
            self._recreate_old_device = ""

    @Slot(str, str)
    def setNetwork(self, ssid: str, password: str) -> None:
        self._ssid = ssid
        self._password = password
        self._emit()

    @Slot(str, str)
    def setIdentity(self, device_name: str, region: str) -> None:
        self._device_name = device_name
        self._region = region
        self._emit()

    @Slot(bool)
    def confirmFactoryRecreate(self, confirmed: bool) -> None:
        self._factory_confirmed = confirmed
        self._emit()

    @Slot()
    def nextStep(self) -> None:
        if self._busy:
            return
        self._step_index = min(self._step_index + 1, len(self._sequence()) - 1)
        self._emit()

    @Slot()
    def previousStep(self) -> None:
        if self._busy:
            return
        self._step_index = max(self._step_index - 1, 0)
        self._emit()

    @Slot()
    def startFlash(self) -> None:
        if self._busy:
            return
        self._error = ""
        self._cancel_status = ""
        self._last_error_code = ""
        self._progress_determinate = False
        self._progress_fraction = None
        self._home_status = ""
        self._recreate_status = ""
        self._recreate_tx_id = ""
        provisioning = (
            None
            if self._mode is CreationMode.UPDATE_EXISTING
            else ProvisioningRequest(
                ssid=self._ssid,
                password=self._password,
                region=self._region,
                device_name=self._device_name,
            )
        )
        request = FactoryRequest(
            mode=self._mode,
            port=self._selected_port,
            board=self._board,
            reference=self._firmware_reference,
            provisioning=provisioning,
            factory_recreate_confirmed=self._factory_confirmed,
            selection=self._firmware_selection,
        )
        # Set busy BEFORE starting: a fast worker must never finish before
        # the flag is set (race that would leave busy stuck at True).
        self._busy = True
        try:
            self._orchestrator.start(request)
        except FactoryError as exc:
            self._busy = False
            self._error = _clean_error(exc)
            self._last_error_code = exc.code
            self.finished.emit(False, self._error)
            self._emit()
            return
        self._step_index = self._sequence().index("flashing")
        self._emit()

    @Slot()
    def cancel(self) -> None:
        self._cancel_status = self._coordinator.request_cancel()
        self._emit()

    @Slot(str)
    def setRecreateOldDevice(self, michi_id: str) -> None:
        # P1 truth: a selection not present in the CURRENT roster never sticks.
        if michi_id and not any(
            item.get("id") == michi_id for item in self.recreateDevices
        ):
            michi_id = ""
        self._recreate_old_device = michi_id
        self._emit()

    @Property(str, notify=stateChanged)
    def recreateStatus(self) -> str:
        return self._recreate_status

    @Property(str, notify=stateChanged)
    def recreateTxId(self) -> str:
        return self._recreate_tx_id

    @Property(str, notify=stateChanged)
    def recreateOldDevice(self) -> str:
        return self._recreate_old_device

    @Property("QVariantList", notify=stateChanged)
    def recreateDevices(self) -> list[dict]:
        if self._recreate_devices_provider is None:
            return []
        try:
            return list(self._recreate_devices_provider())
        except Exception:
            return []

    @Property(str, notify=stateChanged)
    def recreateDeviceName(self) -> str:
        for item in self.recreateDevices:
            if item.get("id") == self._recreate_old_device:
                return str(item.get("name", ""))
        return ""

    # ── coordinator callbacks: queued slots on the owning thread (A2) ───

    @Slot(object)
    def _on_event(self, event: FactoryEvent) -> None:
        self._phase = event.phase.value
        if event.stage is not None:
            self._stage = event.stage.value
            self._progress_determinate = False
            self._progress_fraction = None
        else:
            self._progress_determinate = event.determinate
            self._progress_fraction = event.fraction
        self.progressChanged.emit(self._stage or self._phase)
        self._emit()

    @Slot(object)
    def _on_finished(self, result: FactoryResult) -> None:
        self._busy = False
        self._last_error_code = result.error_code
        self._flash_status = result.flash_status
        self._network_status = result.network_status
        # Host-side truth computed by the orchestrator (worker thread).
        self._home_status = result.home_status
        if result.recreate_status:
            self._recreate_status = result.recreate_status
        if result.recreate_tx_id:
            self._recreate_tx_id = result.recreate_tx_id
        if result.ok:
            if result.reached_ready:
                self._step_index = self._sequence().index("ready")
            else:
                self._step_index = self._sequence().index("discovery")
            self._error = ""
        elif result.cancelled:
            self._error = ""
            self._step_index = self._sequence().index("intro")
        else:
            self._error = result.error or "El flasheo falló."
        self.finished.emit(result.ok, self._error)
        self._emit()

    def _emit(self) -> None:
        self.stateChanged.emit()


def _clean_error(exc: FactoryError) -> str:
    message = getattr(exc, "message", "")
    return message or str(exc)
