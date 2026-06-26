"""Album controller — actions on albums: play, queue, cover search, details."""
import os
import subprocess

from PySide6.QtWidgets import QMessageBox


class AlbumController:
    def __init__(self, window, refresh_grid=None, services=None):
        self._win = window
        self._svc = services
        self._refresh_grid = refresh_grid or (lambda: None)

    def _toast(self, text: str, level: str = "info"):
        self._win._ctx.toast.show(text, level)

    def create_playlist(self, fps: list):
        self._win._ctx.playback.enqueue(fps, play_now=False)
        self._toast("Álbum añadido a la cola", "success")

    def search_cover(self, group):
        tracks = group.data.get("tracks", []) if group.data else []
        if not tracks:
            return
        d = os.path.dirname(tracks[0].filepath)
        try:
            from library.artwork_cache import cache_cover
            from library.cover_art_service import CoverArtService
            cover_path = os.path.join(d, "cover.jpg")
            if os.path.isfile(cover_path):
                from PySide6.QtGui import QPixmap
                pix = QPixmap(cover_path)
                if not pix.isNull():
                    cache_cover(cover_path, pix, "large")
                self._toast("Carátula ya existente", "success")
                self._refresh_grid()
            elif CoverArtService.find_cover(tracks[0].filepath):
                self._toast("Carátula encontrada localmente", "success")
                self._refresh_grid()
            else:
                self._toast("Búsqueda online de carátulas pendiente de implementar", "info")
        except Exception as e:
            self._toast(f"Error al buscar carátula: {e}", "error")

    def open_folder(self, folder: str):
        subprocess.Popen(["xdg-open", folder])

    def show_details(self, group):
        tracks = group.data.get("tracks", []) if group.data else []
        count = len(tracks)
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        dur_str = f"{dur // 60}:{int(dur % 60):02d}" if dur > 0 else "—"
        exts = set(
            (getattr(t, 'ext', '') or '').upper().lstrip(".")
            for t in tracks if getattr(t, 'ext', ''))
        fmt_str = ", ".join(sorted(exts)) or "—"
        msg = (
            f"Álbum: {group.title}\n"
            f"Artista: {group.subtitle or '—'}\n"
            f"Canciones: {count}\n"
            f"Duración: {dur_str}\n"
            f"Formato: {fmt_str}"
        )
        QMessageBox.information(self._win, "Detalles del álbum", msg)
