"""Theme Manager — detect, switch, and apply system theme.

Detects KDE Plasma color scheme via QPalette lightness.
Tries DBus signal for instant notifications, falls back to polling.
"""

import logging

from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from PySide6.QtDBus import QDBusConnection

from ui.design_tokens import set_theme

logger = logging.getLogger("michi.theme")


class ThemeManager(QObject):
    theme_changed = Signal(str)  # "dark" | "light" | "amoled"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "dark"
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.setInterval(5000)
        self._dbus_connected = False

    def detect(self) -> str:
        """Detect system theme from QPalette window color."""
        try:
            app = QApplication.instance()
            if app is None:
                return "dark"
            palette = app.palette()
            lightness = palette.color(QPalette.Window).lightness()
            if lightness <= 20:
                return "amoled"
            elif lightness <= 128:
                return "dark"
            return "light"
        except Exception:
            return "dark"

    def apply(self):
        """Detect and apply theme. Call on startup and on change."""
        detected = self.detect()
        if detected != self._current:
            self._current = detected
            set_theme(detected)
            self.theme_changed.emit(detected)
            logger.info("Theme changed to %s", detected)

    def start_polling(self):
        self._poll_timer.start()

    def stop_polling(self):
        self._poll_timer.stop()

    def _poll(self):
        self.apply()

    def connect_dbus(self):
        """Try connecting to KDE theme change signal via DBus."""
        try:
            bus = QDBusConnection.sessionBus()
            bus.connect(
                "org.kde.KGlobalSettings",
                "/KGlobalSettings",
                "org.kde.KGlobalSettings",
                "notifyChange",
                self._on_dbus_notify,
            )
            self._dbus_connected = True
            logger.debug("DBus theme listener connected")
            self.stop_polling()
        except Exception as e:
            logger.debug("DBus theme listener unavailable, using polling: %s", e)
            self._dbus_connected = False

    def _on_dbus_notify(self, change_type: int, arg: int):
        # change_type 0 = palette changed
        if change_type == 0:
            self.apply()

    @property
    def theme(self) -> str:
        return self._current


def create_theme_manager(parent=None) -> ThemeManager:
    mgr = ThemeManager(parent)
    mgr.apply()
    mgr.connect_dbus()
    if not mgr._dbus_connected:
        mgr.start_polling()
    return mgr
