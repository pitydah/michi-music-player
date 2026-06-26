"""Playlist controller — Hub actions, import/export, smart playlists."""
import os

from PySide6.QtWidgets import QFileDialog, QInputDialog


class PlaylistController:
    def __init__(self, window, services=None):
        self._win = window
        self._svc = services

    def _toast(self, text: str, level: str = "info"):
        self._win._ctx.toast.show(text, level)

    # ── M3U Import ──

    def import_m3u(self):
        path, _ = QFileDialog.getOpenFileName(
            self._win, "Importar M3U", "",
            "Playlist M3U (*.m3u *.m3u8);;Todos (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # Extended M3U (#EXTM3U) vs simple (one filepath per line)
            filepaths = []
            name = os.path.splitext(os.path.basename(path))[0]
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    if line.startswith("#PLAYLIST:") and not name:
                        name = line[len("#PLAYLIST:"):].strip()
                    continue
                fp = os.path.join(os.path.dirname(path), line)
                if os.path.isfile(fp):
                    filepaths.append(fp)
            if not filepaths:
                self._toast("No se encontraron archivos validos en el M3U", "error")
                return
            pid = self._win._ctx.db.create_playlist(name)
            for fp in filepaths:
                self._win._ctx.db.add_to_playlist(pid, fp)
            self._win._ctx.rebuild_sidebar()
            self._toast(f"Importados {len(filepaths)} temas como '{name}'", "success")
        except (OSError, UnicodeDecodeError) as e:
            self._toast(f"Error al importar M3U: {e}", "error")

    # ── M3U Export ──

    def export_playlists(self):
        playlists = self._win._ctx.db.get_playlists()
        if not playlists:
            self._toast("No hay playlists para exportar", "info")
            return
        names = [p["name"] for p in playlists]
        name, ok = QInputDialog.getItem(
            self._win, "Exportar playlist", "Selecciona:", names, 0, False)
        if not ok or not name:
            return
        pl = next((p for p in playlists if p["name"] == name), None)
        if not pl:
            return
        path, _ = QFileDialog.getSaveFileName(
            self._win, "Guardar M3U", f"{name}.m3u",
            "Playlist M3U (*.m3u);;Todos (*.*)")
        if not path:
            return
        try:
            items = self._win._ctx.db.get_playlist_items(pl["id"])
            with open(path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{name}\n")
                for item in items:
                    f.write(f"{item.filepath}\n")
            self._toast(f"Exportada '{name}' con {len(items)} temas", "success")
        except OSError as e:
            self._toast(f"Error al exportar: {e}", "error")

    # ── Playlist from folder ──

    def hub_create_from_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self._win, "Seleccionar carpeta musical")
        if not folder:
            return
        from library.library_db import AUDIO_EXTS
        filepaths = []
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    filepaths.append(os.path.join(root, f))
        if not filepaths:
            self._toast("No se encontraron archivos de audio en la carpeta", "info")
            return
        name = os.path.basename(folder.rstrip("/"))
        pid = self._win._ctx.db.create_playlist(name)
        for fp in filepaths:
            self._win._ctx.db.add_to_playlist(pid, fp)
        self._win._ctx.rebuild_sidebar()
        self._toast(f"Creada '{name}' con {len(filepaths)} temas", "success")

    # ── Playlist from queue ──

    def hub_create_from_queue(self):
        queue = getattr(self._win._ctx.playback, '_queue', [])
        if not queue:
            self._toast("La cola de reproducción está vacía", "info")
            return
        name, ok = QInputDialog.getText(
            self._win, "Crear playlist desde cola", "Nombre:")
        if not ok or not name.strip():
            return
        name = name.strip()
        pid = self._win._ctx.db.create_playlist(name)
        for fp in queue:
            if os.path.isfile(fp):
                self._win._ctx.db.add_to_playlist(pid, fp)
        self._win._ctx.rebuild_sidebar()
        self._toast(f"Creada '{name}' con {len(queue)} temas", "success")

    # ── Create from album/artist/genre/search ──

    def create_from_album(self):
        all_items = getattr(self._win, '_all_items', [])
        if not all_items:
            self._toast("No hay música en la biblioteca", "info")
            return
        from library.artist_grouping import build_artist_albums
        artist_data = build_artist_albums(all_items)
        albums = []
        album_tracks = {}
        for _akey, (agroups, _loose) in artist_data.items():
            for ag in agroups:
                label = f"{ag.title} — {ag.artist}" if ag.artist else ag.title
                albums.append(label)
                album_tracks[label] = ag.tracks
        if not albums:
            self._toast("No se encontraron albumes", "info")
            return
        label, ok = QInputDialog.getItem(
            self._win, "Crear playlist desde album",
            "Selecciona:", sorted(albums), 0, False)
        if not ok or not label:
            return
        tracks = album_tracks.get(label, [])
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            pid = self._win._ctx.db.create_playlist(label[:64])
            for fp in fps:
                self._win._ctx.db.add_to_playlist(pid, fp)
            self._win._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {label[:48]} ({len(fps)} temas)", "success")

    def create_from_artist(self):
        all_items = getattr(self._win, '_all_items', [])
        if not all_items:
            self._toast("No hay música en la biblioteca", "info")
            return
        from library.artist_grouping import build_artist_groups
        groups = build_artist_groups(all_items)
        names = sorted(g.display_name for g in groups if g.display_name)
        if not names:
            self._toast("No se encontraron artistas", "info")
            return
        name, ok = QInputDialog.getItem(
            self._win, "Crear playlist desde artista",
            "Selecciona:", names, 0, False)
        if not ok or not name:
            return
        group = next((g for g in groups if g.display_name == name), None)
        if group:
            fps = [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]
            if fps:
                pid = self._win._ctx.db.create_playlist(name)
                for fp in fps:
                    self._win._ctx.db.add_to_playlist(pid, fp)
                self._win._ctx.rebuild_sidebar()
                self._toast(f"Playlist creada: {name} ({len(fps)} temas)", "success")

    def create_from_genre(self):
        all_items = getattr(self._win, '_all_items', [])
        if not all_items:
            self._toast("No hay música en la biblioteca", "info")
            return
        genres = sorted(set(i.genre for i in all_items if i.genre))
        if not genres:
            self._toast("No se encontraron generos", "info")
            return
        genre, ok = QInputDialog.getItem(
            self._win, "Crear playlist desde genero",
            "Selecciona:", genres, 0, False)
        if not ok or not genre:
            return
        tracks = [i for i in all_items if i.genre == genre]
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            pid = self._win._ctx.db.create_playlist(genre)
            for fp in fps:
                self._win._ctx.db.add_to_playlist(pid, fp)
            self._win._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {genre} ({len(fps)} temas)", "success")

    def create_from_search(self):
        model = self._win._ctx.model
        if not model or model.rowCount() == 0:
            self._toast("No hay resultados de busqueda activos", "info")
            return
        name, ok = QInputDialog.getText(
            self._win, "Crear playlist desde busqueda", "Nombre:")
        if not ok or not name.strip():
            return
        name = name.strip()
        fps = []
        for row in range(model.rowCount()):
            ref = model.get_trackref(row)
            fp = ref.uri if ref else ""
            if fp and os.path.isfile(fp):
                fps.append(fp)
        if fps:
            pid = self._win._ctx.db.create_playlist(name)
            for fp in fps:
                self._win._ctx.db.add_to_playlist(pid, fp)
            self._win._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {name} ({len(fps)} temas)", "success")

    # ── Hub navigation ──

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
        self._toast("Playlist anadida a la cola", "success")

    # ── CRUD helpers ──

    def metadata_saved(self, filepaths: list):
        self._toast(f"Metadatos guardados en {len(filepaths)} archivos", "success")

    def refresh_library(self):
        self._win._ctx.load_library()
