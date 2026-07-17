"""AppStateBridge — global QML application state with independent modes."""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


class AppStateBridge(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("AppStateBridge.__init__ called")
        self._safe_mode = False
        self._delivery_mode = os.environ.get("MICHI_QML_DELIVERY_MODE") == "1"
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
    def deliveryMode(self):
        return self._delivery_mode

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

    @Slot(bool, bool, str)
    def setServiceAvailability(self, player_ok: bool, db_ok: bool, audio_status: str):
        self._player_available = player_ok
        self._db_available = db_ok
        self._audio_status = audio_status if audio_status else ("available" if player_ok else "unavailable")
        if os.environ.get("MICHI_SAFE_MODE") == "1":
            self._safe_mode = True
        else:
            self._safe_mode = not player_ok
        self.stateChanged.emit()
