"""QML bridge for the opt-in Home Assistant integration.

Broker connect/disconnect/republish can perform network I/O and therefore run
outside the GUI thread. Errors are normalized before reaching QML so broker
credentials or raw transport exceptions are never surfaced as primary UX.
"""

from __future__ import annotations

import threading
from datetime import datetime

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from michi_ecosystem.application.home_assistant_service import HomeAssistantService
from michi_ecosystem.domain.home_assistant import (
    HomeAssistantConnectionState,
)

_CONNECTION_COPY: dict[HomeAssistantConnectionState, tuple[str, str]] = {
    HomeAssistantConnectionState.DISABLED: ("Desactivado", "neutral"),
    HomeAssistantConnectionState.CONFIGURED: (
        "Configurado, sin activar",
        "neutral",
    ),
    HomeAssistantConnectionState.CONNECTING: ("Conectando…", "active"),
    HomeAssistantConnectionState.CONNECTED: ("Conectado", "success"),
    HomeAssistantConnectionState.RECONNECTING: ("Reconectando…", "warning"),
    HomeAssistantConnectionState.DISCONNECTED: ("Sin conexión al broker", "error"),
    HomeAssistantConnectionState.ERROR: ("Error de conexión", "error"),
    HomeAssistantConnectionState.UNKNOWN: (
        "Estado de conexión no disponible",
        "neutral",
    ),
}

_CONNECTION_ERROR_COPY = {
    "BROKER_CONNECT_FAILED": "No se pudo conectar con el broker MQTT.",
    "BROKER_CONNECTION_ERROR": "El broker informó un error de conexión.",
    "ADAPTER_ERROR": "No se pudo consultar el estado de la conexión.",
}


class HomeAssistantBridge(QObject):
    stateChanged = Signal()
    operationFinished = Signal(bool, str)
    _completed = Signal(str, bool, str)
    _connection_changed = Signal()

    def __init__(
        self, service: HomeAssistantService | None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._error = ""
        self._busy = False
        self._completed.connect(self._on_completed, Qt.ConnectionType.QueuedConnection)
        # Transport callbacks may arrive on MQTT threads: marshal to the GUI
        # thread before any QML property notification.
        self._connection_changed.connect(
            self.stateChanged.emit, Qt.ConnectionType.QueuedConnection
        )

    @Property(bool, notify=stateChanged)
    def available(self) -> bool:
        return self._service is not None

    @Property(bool, notify=stateChanged)
    def configurable(self) -> bool:
        return self._service is not None and self._service.configurable

    @Property("QVariantMap", notify=stateChanged)
    def configuration(self) -> dict:
        if self._service is None:
            return {}
        config = self._service.configuration()
        return {
            "broker": config.broker,
            "port": config.port,
            "tls": config.tls,
            "username": config.username,
            "autoDiscovery": config.auto_discovery,
            "publishDevices": config.publish_devices,
            "diagnostics": config.diagnostics,
        }

    @Property(bool, notify=stateChanged)
    def enabled(self) -> bool:
        return self._service is not None and self._service.enabled

    def _connection_state(self) -> HomeAssistantConnectionState:
        if self._service is None:
            return HomeAssistantConnectionState.DISABLED
        try:
            return self._service.connection_state
        except Exception:
            return HomeAssistantConnectionState.ERROR

    @Property(str, notify=stateChanged)
    def connectionState(self) -> str:
        return self._connection_state().value

    @Property(str, notify=stateChanged)
    def connectionText(self) -> str:
        return _CONNECTION_COPY[self._connection_state()][0]

    @Property(str, notify=stateChanged)
    def connectionTone(self) -> str:
        return _CONNECTION_COPY[self._connection_state()][1]

    @Property(str, notify=stateChanged)
    def connectionDetail(self) -> str:
        state = self._connection_state()
        if state in (
            HomeAssistantConnectionState.ERROR,
            HomeAssistantConnectionState.DISCONNECTED,
        ):
            code = self._service.last_error_code if self._service is not None else ""
            return _CONNECTION_ERROR_COPY.get(
                code, "Revisa la configuración MQTT del broker."
            )
        if (
            state is HomeAssistantConnectionState.CONNECTED
            and self._service is not None
        ):
            published = self._service.last_publish_ok_ms
            if published is not None:
                moment = datetime.fromtimestamp(published / 1000.0)
                return f"Última publicación: {moment:%H:%M:%S}"
        return ""

    @Slot()
    def notify_connection_changed(self) -> None:
        """Thread-safe entry point for service/transport connectivity events."""
        self._connection_changed.emit()

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        if self._service is None:
            self._finish_sync(False, "Home Assistant no está configurado en este host")
            return
        if self._busy:
            return
        self._start(
            "enable" if enabled else "disable",
            self._service.enable if enabled else self._service.disable,
        )

    @Slot()
    def republish(self) -> None:
        if self._service is None or not self._service.enabled or self._busy:
            return
        self._start("republish", self._service.republish)

    @Slot(str, int, bool, str, str, bool, bool, bool)
    def saveConfiguration(
        self,
        broker: str,
        port: int,
        tls: bool,
        username: str,
        password: str,
        auto_discovery: bool,
        publish_devices: bool,
        diagnostics: bool,
    ) -> None:
        if self._service is None or not self._service.configurable:
            self._finish_sync(
                False, "La configuración MQTT no está disponible en este host"
            )
            return
        if self._busy or self._service.enabled:
            self._finish_sync(False, "Desactiva Home Assistant antes de cambiar MQTT")
            return
        self._start(
            "configure",
            lambda: self._service.configure(
                broker=broker,
                port=port,
                tls=tls,
                username=username,
                password=password or None,
                auto_discovery=auto_discovery,
                publish_devices=publish_devices,
                diagnostics=diagnostics,
            ),
        )

    def _start(self, operation: str, work) -> None:
        self._busy = True
        self._error = ""
        self.stateChanged.emit()

        def run() -> None:
            try:
                work()
            except Exception:
                message = {
                    "enable": "No pudimos conectar con el broker MQTT",
                    "configure": "No pudimos guardar la configuración MQTT",
                }.get(operation, "No pudimos actualizar Home Assistant")
                self._completed.emit(operation, False, message)
            else:
                messages = {
                    "enable": "Home Assistant activado",
                    "disable": "Home Assistant desactivado",
                    "republish": "Discovery y estado republicados",
                    "configure": "Configuración MQTT guardada",
                }
                self._completed.emit(operation, True, messages[operation])

        threading.Thread(
            target=run,
            name=f"michi-home-assistant-{operation}",
            daemon=True,
        ).start()

    @Slot(str, bool, str)
    def _on_completed(self, _operation: str, ok: bool, message: str) -> None:
        self._busy = False
        self._error = "" if ok else message
        self.stateChanged.emit()
        self.operationFinished.emit(ok, message)

    def _finish_sync(self, ok: bool, message: str) -> None:
        self._error = "" if ok else message
        self.stateChanged.emit()
        self.operationFinished.emit(ok, message)
