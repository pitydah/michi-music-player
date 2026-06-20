"""Tray controller — manages system tray icon and notifications."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from ui.icons import get_icon


class TrayController:
    def __init__(self, window):
        self._win = window
        self._icon: QSystemTrayIcon | None = None

    def setup(self):
        tray_pix = QPixmap(get_icon("tray_icon"))
        if not tray_pix.isNull():
            tray_pix = tray_pix.scaled(64, 64, Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation)
        self._icon = QSystemTrayIcon(QIcon(tray_pix), self._win)
        self._icon.setToolTip("Astra Music Player")
        tray_menu = QMenu()
        tray_menu.addAction("Mostrar", self._win.show)
        tray_menu.addAction("Reproducir/Pausa", self._win._playback.toggle)
        tray_menu.addAction("Siguiente", self._win._playback.play_next)
        tray_menu.addAction("Anterior", self._win._playback.play_prev)
        tray_menu.addSeparator()
        tray_menu.addAction("Salir", self._win.close)
        self._icon.setContextMenu(tray_menu)
        self._icon.show()

    def notify(self, title: str, artist: str):
        if self._icon and self._icon.isVisible():
            self._icon.showMessage(
                "Astra", f"{title} — {artist}",
                QSystemTrayIcon.NoIcon, 3000)
