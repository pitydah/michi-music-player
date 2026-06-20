"""Playlist controller — Hub actions, import/export, smart playlists."""
import os

from PySide6.QtWidgets import QFileDialog


class PlaylistController:
    def __init__(self, window):
        self._win = window

    def import_m3u(self):
        path, _ = QFileDialog.getOpenFileName(
            self._win, "Importar M3U", "", "Playlist M3U (*.m3u *.m3u8);;Todos (*.*)")
        if path:
            self._win._toast.show(
                f"Importador M3U pendiente de implementar: {os.path.basename(path)}", "info")

    def export_playlists(self):
        self._win._toast.show("Exportador de playlists pendiente de implementar", "info")

    def open_smart_playlist(self, key: str):
        self._win._on_sidebar_navigate(
            f"mix_{key}" if not key.startswith("mix_") else key)

    def hub_playlist_play(self, pid: int):
        items = self._win._db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._win._playback.enqueue(fps, play_now=True)
        self._win._toast.show("Reproduciendo playlist", "success")

    def hub_playlist_queue(self, pid: int):
        items = self._win._db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._win._playback.enqueue(fps, play_now=False)
        self._win._toast.show("Playlist añadida a la cola", "success")

    def hub_create_from_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self._win, "Seleccionar carpeta musical")
        if folder:
            self._win._toast.show(
                f"Crear playlist desde carpeta pendiente: {folder}", "info")

    def hub_create_from_queue(self):
        self._win._toast.show(
            "Crear playlist desde cola pendiente de implementar", "info")

    def stub_action(self):
        self._win._toast.show("Acción pendiente de implementar", "info")

    def metadata_saved(self, filepaths: list):
        self._win._toast.show(
            f"Metadatos guardados en {len(filepaths)} archivos", "success")

    def refresh_library(self):
        self._win._load_library()
