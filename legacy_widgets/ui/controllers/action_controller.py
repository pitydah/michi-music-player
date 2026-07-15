"""ActionController — menus, shortcuts, and app-level actions.

Extracted from MainWindow._setup_actions() to reduce window.py size.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.action_ctrl")


class ActionController:
    def __init__(self, window: MainWindow):
        self._win = window

    def setup(self):
        w = self._win
        from library.metadata_extractor import ALL_EXTS

        self._open_file_action = QAction("Abrir archivo...", w)
        self._open_file_action.setShortcut("Ctrl+O")
        self._open_file_action.triggered.connect(
            lambda: w._file_actions.open_files(ALL_EXTS))
        w.addAction(self._open_file_action)

        self._add_folder_action = QAction("Añadir carpeta...", w)
        self._add_folder_action.setShortcut("Ctrl+D")
        self._add_folder_action.triggered.connect(
            lambda: w._library_import.add_folder(w))
        w.addAction(self._add_folder_action)

        self._import_playlist_action = QAction("Importar playlist...", w)
        self._import_playlist_action.triggered.connect(
            lambda: w._playlist_ctrl.import_playlist(
                w, w._db, w._playback, w._player_bar_ctrl, w._load_library))
        w.addAction(self._import_playlist_action)

        self._export_playlist_action = QAction("Exportar playlist...", w)
        self._export_playlist_action.triggered.connect(
            lambda: w._playlist_ctrl.export_queue(w, w._playback))
        w.addAction(self._export_playlist_action)

        self._sync_action = QAction("Activar sincronización Android", w)
        self._sync_action.setCheckable(True)
        self._sync_action.triggered.connect(self._toggle_sync)
        w.addAction(self._sync_action)

        self._preferences_action = QAction("Preferencias...", w)
        self._preferences_action.setShortcut("Ctrl+P")
        self._preferences_action.triggered.connect(w._show_preferences)
        w.addAction(self._preferences_action)

        back_action = QAction(w)
        back_action.setShortcut("Alt+Left")
        back_action.triggered.connect(lambda: w._nav_ctrl.navigate_back())
        w.addAction(back_action)

        forward_action = QAction(w)
        forward_action.setShortcut("Alt+Right")
        forward_action.triggered.connect(lambda: w._nav_ctrl.navigate_forward())
        w.addAction(forward_action)

        self._add_transmit_device_action = QAction("Añadir dispositivo...", w)
        self._add_transmit_device_action.triggered.connect(
            lambda: w._transmit_ctrl.add_device())
        w.addAction(self._add_transmit_device_action)

        self._manage_transmit_devices_action = QAction("Administrar dispositivos...", w)
        self._manage_transmit_devices_action.triggered.connect(
            lambda: w._transmit_ctrl.manage_devices())
        w.addAction(self._manage_transmit_devices_action)

        self._shortcuts_action = QAction("Atajos de teclado", w)
        self._shortcuts_action.triggered.connect(w._show_shortcuts)
        w.addAction(self._shortcuts_action)

        self._about_action = QAction("Acerca de", w)
        self._about_action.triggered.connect(w._show_about)
        w.addAction(self._about_action)

        self._duplicates_action = QAction("Buscar duplicados...", w)
        self._duplicates_action.triggered.connect(self._show_duplicates)
        w.addAction(self._duplicates_action)

        self._quit_action = QAction("Salir", w)
        self._quit_action.setShortcut("Ctrl+Q")
        self._quit_action.triggered.connect(w.close)
        w.addAction(self._quit_action)

        w.menuBar().hide()

    def _toggle_sync(self):
        w = self._win
        mgr = w._ensure_sync_manager()
        if mgr.is_active:
            mgr.stop()
            self._sync_action.setChecked(False)
        else:
            mgr.start()
            self._sync_action.setChecked(True)

    def _show_duplicates(self):
        from ui.dialogs.duplicate_dialog import DuplicateDialog
        dlg = DuplicateDialog(self._win._db, self._win)
        dlg.exec()
