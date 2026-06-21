"""Playlist controller — Hub actions, import/export, smart playlists."""
import os

from PySide6.QtWidgets import QFileDialog


class PlaylistController:
    def __init__(self, window):
        self._win = window

    def _toast(self, text: str, level: str = "info"):
        self._win._ctx.toast.show(text, level)

    def import_m3u(self):
        path, _ = QFileDialog.getOpenFileName(
            self._win, "Importar M3U", "", "Playlist M3U (*.m3u *.m3u8);;Todos (*.*)")
        if path:
            self._toast(f"Importador M3U pendiente de implementar: {os.path.basename(path)}", "info")

    def export_playlists(self):
        self._toast("Exportador de playlists pendiente de implementar", "info")

    def open_smart_playlist(self, key: str):
        self._win._ctx.navigate_sidebar(
            f"mix_{key}" if not key.startswith("mix_") else key)

    def hub_playlist_play(self, pid: int):
        items = self._win._ctx.db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._win._play_filepaths(fps, play_now=True)
        self._toast("Reproduciendo playlist", "success")

    def hub_playlist_queue(self, pid: int):
        items = self._win._ctx.db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._win._ctx.playback.enqueue(fps, play_now=False)
        self._toast("Playlist añadida a la cola", "success")

    def hub_create_from_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self._win, "Seleccionar carpeta musical")
        if folder:
            self._toast(f"Crear playlist desde carpeta pendiente: {folder}", "info")

    def hub_create_from_queue(self):
        self._toast("Crear playlist desde cola pendiente de implementar", "info")

    def stub_action(self):
        self._toast("Acción pendiente de implementar", "info")

    def metadata_saved(self, filepaths: list):
        self._toast(f"Metadatos guardados en {len(filepaths)} archivos", "success")

    def refresh_library(self):
        self._win._ctx.load_library()
