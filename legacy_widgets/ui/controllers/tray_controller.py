"""Tray controller — manages system tray icon and notifications."""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from ui.icon_loader import get_tray_icon


class TrayController:
    def __init__(self, window, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services
        self._icon: QSystemTrayIcon | None = None

    def setup(self):
        self._icon = QSystemTrayIcon(get_tray_icon(), self._win)
        self._icon.setToolTip("Michi Music Player")

        tray_menu = QMenu()
        tray_menu.addAction("Mostrar", self._win.show)
        tray_menu.addAction("Reproducir/Pausa", self._ctx.playback.toggle)
        tray_menu.addAction("Siguiente", self._ctx.playback.play_next)
        tray_menu.addAction("Anterior", self._ctx.playback.play_prev)
        tray_menu.addSeparator()
        tray_menu.addAction("Salir", self._win.close)

        self._icon.setContextMenu(tray_menu)
        self._icon.show()

    @property
    def icon(self):
        """Public access to the system tray icon for window-level wiring."""
        return self._icon

    def notify(self, title: str, artist: str):
        if self._icon and self._icon.isVisible():
            self._icon.showMessage(
                "Michi", f"{title} — {artist}",
                QSystemTrayIcon.NoIcon, 3000)
