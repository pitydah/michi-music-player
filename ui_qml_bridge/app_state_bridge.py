"""AppStateBridge — global QML application state."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class AppStateBridge(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._safe_mode = False
        self._qml_mode = True
        self._app_version = "0.2.0a0"
        self._current_route = "home"
        self._player_available = False
        self._db_available = False
        self._is_busy = False
        self._busy_message = ""
        self._startup_warnings: list[str] = []
        self._runtime_warnings: list[str] = []
        self._audio_status = "unavailable"

    @Property(bool, notify=stateChanged)
    def safeMode(self):
        return self._safe_mode

    @Property(bool, notify=stateChanged)
    def qmlMode(self):
        return self._qml_mode

    @Property(str, notify=stateChanged)
    def appVersion(self):
        return self._app_version

    @Property(str, notify=stateChanged)
    def currentRoute(self):
        return self._current_route

    @Property(bool, notify=stateChanged)
    def playerAvailable(self):
        return self._player_available

    @Property(bool, notify=stateChanged)
    def dbAvailable(self):
        return self._db_available

    @Property(str, notify=stateChanged)
    def audioStatus(self):
        return self._audio_status

    @Property(bool, notify=stateChanged)
    def isBusy(self):
        return self._is_busy

    @Property(str, notify=stateChanged)
    def busyMessage(self):
        return self._busy_message

    @Property("QVariantList", notify=stateChanged)
    def startupWarnings(self):
        return self._startup_warnings

    @Property("QVariantList", notify=stateChanged)
    def runtimeWarnings(self):
        return self._runtime_warnings

    @Slot()
    def refresh(self):
        self.stateChanged.emit()

    @Slot(str)
    def setBusy(self, message: str):
        self._is_busy = True
        self._busy_message = message
        self.stateChanged.emit()

    @Slot()
    def clearBusy(self):
        self._is_busy = False
        self._busy_message = ""
        self.stateChanged.emit()

    @Slot(str, str)
    def pushWarning(self, source: str, message: str):
        self._runtime_warnings.append(f"[{source}] {message}")
        if len(self._runtime_warnings) > 50:
            self._runtime_warnings.pop(0)
        self.stateChanged.emit()

    @Slot()
    def clearWarnings(self):
        self._runtime_warnings.clear()
        self.stateChanged.emit()

    def _update_availability(self):
        pass
