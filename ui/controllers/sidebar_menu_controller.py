"""SidebarMenuController — contextual sidebar menu and playlist CRUD dialogs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QInputDialog, QLineEdit,
    QMenu, QPushButton, QDialogButtonBox,
)

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.sidebar_menu")


class SidebarMenuController:
    """Handles right-click context menu on sidebar items + playlist CRUD."""

    def __init__(self, window: MainWindow):
        self._win = window

    # ── Context menu ──

    def show_context_menu(self, pos):
        w = self._win
        widget = w._sidebar.childAt(pos)
        from ui.sidebar.sidebar_item import SidebarItem
        item = None
        while widget:
            if isinstance(widget, SidebarItem):
                item = widget
                break
            widget = widget.parentWidget()
        if not item:
            return
        key = item.key
        menu = QMenu(w)

        if key and key.startswith("pl:"):
            pid = int(key.split(":", 1)[1])
            menu.addAction("Eliminar playlist", lambda: self._win._delete_playlist(pid))
        elif key and key.startswith("srv:"):
            name = key.split(":", 1)[1]
            menu.addAction("Eliminar servidor", lambda: self._win._srv_ctrl.remove_server(name))

        if not menu.isEmpty():
            menu.exec(w._sidebar._container.mapToGlobal(pos))

    # ── Playlist CRUD ──

    def create_playlist(self):
        w = self._win
        name, ok = QInputDialog.getText(w, "Nueva playlist", "Nombre:")
        if ok and name.strip():
            w._db.create_playlist(name.strip())
            w._rebuild_sidebar()

    def delete_playlist(self, pid):
        w = self._win
        w._db.delete_playlist(pid)
        w._rebuild_sidebar()
        w._load_library()

    def edit_playlist_dialog(self, pid: int):
        w = self._win
        pl = next((p for p in w._db.get_playlists() if p["id"] == pid), None)
        if not pl:
            return

        dlg = QDialog(w)
        dlg.setWindowTitle(f"Editar playlist — {pl['name']}")
        dlg.setMinimumWidth(400)
        layout = QFormLayout(dlg)

        name_edit = QLineEdit(pl.get("name", ""))
        layout.addRow("Nombre:", name_edit)

        desc_edit = QLineEdit(pl.get("description", ""))
        layout.addRow("Descripción:", desc_edit)

        cover_btn = QPushButton("Cambiar portada")
        cover_btn.clicked.connect(lambda: self._change_playlist_cover(pid))
        layout.addRow("Portada:", cover_btn)

        remove_btn = QPushButton("Quitar portada")
        remove_btn.clicked.connect(lambda: self._remove_playlist_cover(pid))
        layout.addRow("", remove_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(
            lambda: self._save_playlist_edit(pid, name_edit.text(), desc_edit.text(), dlg))
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)

        dlg.exec()

    def _change_playlist_cover(self, pid: int):
        w = self._win
        path, _ = QFileDialog.getOpenFileName(
            w, "Seleccionar portada", "",
            "Imágenes (*.jpg *.jpeg *.png);;Todos (*)")
        if path:
            from ui.services.playlist_cover_service import copy_custom_cover
            cover_path = copy_custom_cover(pid, path)
            w._db.update_playlist(pid, cover_path=cover_path, cover_type="custom")
            w._toast_svc.show("Portada actualizada", "success")

    def _remove_playlist_cover(self, pid: int):
        w = self._win
        from ui.services.playlist_cover_service import remove_custom_cover
        remove_custom_cover(pid)
        w._db.update_playlist(pid, cover_path="", cover_type="mosaic")
        w._toast_svc.show("Portada eliminada — se usará mosaico automático", "info")

    def _save_playlist_edit(self, pid: int, name: str, desc: str, dlg):
        w = self._win
        w._db.update_playlist(pid, name=name, description=desc)
        w._rebuild_sidebar()
        w._toast_svc.show("Playlist actualizada", "success")
        dlg.accept()
