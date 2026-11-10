"""QML bridge for Music Stream detail pages and normal lifecycle actions."""

from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.stream_management_service import (
    StreamManagementError,
    StreamManagementService,
)


class StreamDeviceBridge(QObject):
    streams_changed = Signal()
    selected_changed = Signal()
    error_occurred = Signal(str, str)
    operation_finished = Signal(bool, str)
    busy_changed = Signal()
    diagnostics_changed = Signal()
    _completed = Signal(bool, str, str)
    _diagnostics_ready = Signal(str, "QVariantMap")
    _registry_refresh_requested = Signal()

    def __init__(
        self, service: StreamManagementService, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._selected_id = ""
        self._busy = False
        self._diagnostics: dict[str, dict[str, Any]] = {}
        self._completed.connect(self._on_completed, Qt.ConnectionType.QueuedConnection)
        self._diagnostics_ready.connect(
            self._on_diagnostics_ready, Qt.ConnectionType.QueuedConnection
        )
        self._registry_refresh_requested.connect(
            self.refresh, Qt.ConnectionType.QueuedConnection
        )

    @Property(bool, notify=busy_changed)
    def busy(self) -> bool:
        return self._busy

    def _run_action(self, name: str, work) -> None:
        if self._busy:
            self.error_occurred.emit("STREAM_BUSY", "Ya existe una operación en curso")
            return
        self._busy = True
        self.busy_changed.emit()

        def worker() -> None:
            try:
                work()
            except StreamManagementError as exc:
                self._completed.emit(False, exc.code, exc.message)
            except Exception:
                # Never project adapter exceptions, URLs or credentials to QML.
                self._completed.emit(
                    False, "STREAM_OPERATION_FAILED", "La operación falló"
                )
            else:
                self._completed.emit(True, name, "")

        try:
            threading.Thread(
                target=worker, name="michi-stream-management", daemon=True
            ).start()
        except Exception:
            self._busy = False
            self.busy_changed.emit()
            self.error_occurred.emit(
                "STREAM_OPERATION_FAILED", "No se pudo iniciar la operación"
            )

    @Slot(bool, str, str)
    def _on_completed(self, ok: bool, code: str, message: str) -> None:
        self._busy = False
        self.busy_changed.emit()
        self.refresh()
        if not ok:
            self.error_occurred.emit(code, message)
            self.operation_finished.emit(False, message)
        else:
            self.operation_finished.emit(True, code)

    def on_registry_changed(self, _devices) -> None:
        """Registry listener: keep list/detail projections live without polling."""
        self._registry_refresh_requested.emit()

    @Property("QVariantList", notify=streams_changed)
    def streams(self) -> list[dict[str, Any]]:
        return [
            self._service.detail(device.canonical_id)
            for device in self._service.list_streams()
        ]

    @Property("QVariantMap", notify=selected_changed)
    def selectedDevice(self) -> dict[str, Any]:
        if not self._selected_id:
            return {}
        try:
            return self._service.detail(self._selected_id)
        except StreamManagementError:
            return {}

    @Slot()
    def refresh(self) -> None:
        self.streams_changed.emit()
        self.selected_changed.emit()

    @Slot(str)
    def select(self, canonical_id: str) -> None:
        try:
            self._service.get_stream(canonical_id)
        except StreamManagementError as exc:
            self.error_occurred.emit(exc.code, exc.message)
            return
        self._selected_id = canonical_id
        self.selected_changed.emit()

    @Property("QVariantMap", notify=diagnostics_changed)
    def lastDiagnostics(self) -> dict[str, Any]:
        """Last receiver report for the selected device (unfrozen schema)."""
        if not self._selected_id:
            return {}
        return self._diagnostics.get(self._selected_id, {})

    @Slot(str)
    def diagnostics(self, canonical_id: str) -> None:
        def work() -> None:
            report = self._service.run_diagnostics(canonical_id)
            # Marshal to the GUI thread: the worker must never touch QML state.
            self._diagnostics_ready.emit(str(canonical_id), dict(report))

        self._run_action("Diagnóstico actualizado", work)

    @Slot(str, "QVariantMap")
    def _on_diagnostics_ready(self, canonical_id: str, report: dict[str, Any]) -> None:
        self._diagnostics[canonical_id] = dict(report)
        self.diagnostics_changed.emit()

    @Slot(str)
    def updateFirmware(self, canonical_id: str) -> None:
        self._run_action(
            "Actualización solicitada",
            lambda: self._service.request_firmware_update(canonical_id),
        )

    @Slot(str)
    def reprovisionNetwork(self, canonical_id: str) -> None:
        self._run_action(
            "Configuración de red iniciada",
            lambda: self._service.reprovision_network(canonical_id),
        )
