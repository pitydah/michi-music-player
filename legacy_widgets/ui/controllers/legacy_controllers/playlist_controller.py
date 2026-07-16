"""Playlist controller — Hub actions, import/export, smart playlists."""
import os

from PySide6.QtWidgets import QFileDialog, QInputDialog


class PlaylistController:
    def __init__(self, window, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def _context(self):
        return (
            getattr(self._svc, "context_svc", None)
            or getattr(self._ctx, "context_svc", None)
        )

    def _select_playlist(self, pid: int, name: str = ""):
        ctx = self._context()
        if ctx:
            ctx.update_selection(
                scope="playlist",
                playlist_id=pid,
                playlist_name=name,
                album="", artist="", genre="",
                folder_name="", mix_key="", search_query="",
            )

    def _record_playlist_created(self, pid: int, name: str, count: int):
        self._select_playlist(pid, name)
        ctx = self._context()
        if ctx:
            ctx.record_playlist_created(playlist_id=pid, name=name, count=count)

    def _toast(self, text: str, level: str = "info"):
        if self._ctx and hasattr(self._ctx, 'toast'):
            self._ctx.toast.show(text, level)

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
            pid = self._ctx.db.create_playlist(name)
            for fp in filepaths:
                self._ctx.db.add_to_playlist(pid, fp)
            self._ctx.rebuild_sidebar()
            self._toast(f"Importados {len(filepaths)} temas como '{name}'", "success")
            ctx = self._context()
            if ctx:
                ctx.record_playlist_imported(pid, name, len(filepaths))
        except (OSError, UnicodeDecodeError) as e:
            self._toast(f"Error al importar M3U: {e}", "error")

    # ── M3U Export ──

    def export_playlists(self):
        playlists = self._ctx.db.get_playlists()
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
            items = self._ctx.db.get_playlist_items(pl["id"])
            with open(path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{name}\n")
                for item in items:
                    f.write(f"{item.filepath}\n")
            self._toast(f"Exportada '{name}' con {len(items)} temas", "success")
            ctx = self._context()
            if ctx:
                ctx.record_playlist_exported(pl["id"], name, len(items))
        except OSError as e:
            self._toast(f"Error al exportar: {e}", "error")

    def import_playlist(self, parent, db, playback, player_bar_ctrl, load_library):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            parent, "Importar playlist", os.path.expanduser("~"),
            "Playlists (*.m3u *.m3u8 *.pls);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import parse_playlist_entries
        entries = parse_playlist_entries(path)
        if not entries:
            QMessageBox.information(
                parent, "Importar", "No se encontraron entradas en la playlist.")
            return

        valid_files = []
        missing = 0
        remote = 0
        for e in entries:
            if e.is_remote:
                remote += 1
                continue
            if e.exists:
                db.add_file(e.resolved_path)
                valid_files.append(e.resolved_path)
            else:
                missing += 1

        load_library()
        if valid_files:
            playback.enqueue(valid_files, play_now=False)
        player_bar_ctrl.set_track(
            f"Importados {len(valid_files)} temas", "Playlist")

        summary = f"<p><b>{len(valid_files)}</b> archivos añadidos a la biblioteca.</p>"
        if missing:
            summary += f"<p><b>{missing}</b> archivos no encontrados en disco.</p>"
        if remote:
            summary += f"<p><b>{remote}</b> entradas remotas ignoradas.</p>"
        summary += f"<p>Total entradas en playlist: <b>{len(entries)}</b></p>"
        QMessageBox.information(parent, "Importar playlist", summary)

        ctx = self._context()
        if ctx:
            ctx.record_playlist_imported(0, os.path.basename(path), len(valid_files))

    def export_queue(self, parent, playback):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        queue = playback.get_queue()
        if not queue:
            QMessageBox.information(
                parent, "Exportar", "La cola de reproducción está vacía.")
            return
        path, _ = QFileDialog.getSaveFileName(
            parent, "Exportar playlist", "playlist.m3u",
            "M3U (*.m3u);;Todos (*)")
        if not path:
            return
        from ui.playlist_io import export_m3u
        export_m3u(path, [q["filepath"] for q in queue])
        QMessageBox.information(
            parent, "Exportar", f"Playlist exportada a {path}")

        ctx = self._context()
        if ctx:
            ctx.record_playlist_exported(0, os.path.basename(path), len(queue))

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
        pid = self._ctx.db.create_playlist(name)
        for fp in filepaths:
            self._ctx.db.add_to_playlist(pid, fp)
        self._ctx.rebuild_sidebar()
        self._toast(f"Creada '{name}' con {len(filepaths)} temas", "success")
        self._record_playlist_created(pid, name, len(filepaths))

    # ── Playlist from queue ──

    def hub_create_from_queue(self):
        playback = self._svc.playback if self._svc and hasattr(self._svc, 'playback') else self._ctx.playback
        queue = playback.get_queue() if hasattr(playback, 'get_queue') else []
        if not queue:
            self._toast("La cola de reproducción está vacía", "info")
            return
        name, ok = QInputDialog.getText(
            self._win, "Crear playlist desde cola", "Nombre:")
        if not ok or not name.strip():
            return
        name = name.strip()
        pid = self._ctx.db.create_playlist(name)
        for q in queue:
            fp = q.get("filepath", q) if isinstance(q, dict) else q
            if os.path.isfile(fp):
                self._ctx.db.add_to_playlist(pid, fp)
        self._ctx.rebuild_sidebar()
        self._toast(f"Creada '{name}' con {len(queue)} temas", "success")
        self._record_playlist_created(pid, name, len(queue))

    # ── Create from album/artist/genre/search ──

    def _all_library_tracks(self) -> list:
        """Return all tracks from the library, preferring injected db."""
        if self._svc and hasattr(self._svc, 'db'):
            return self._svc.db.get_all()
        return self._ctx.all_items_list

    def create_from_album(self):
        all_items = self._all_library_tracks()
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
            self._toast("No se encontraron álbumes", "info")
            return
        label, ok = QInputDialog.getItem(
            self._win, "Crear playlist desde album",
            "Selecciona:", sorted(albums), 0, False)
        if not ok or not label:
            return
        tracks = album_tracks.get(label, [])
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            pid = self._ctx.db.create_playlist(label[:64])
            for fp in fps:
                self._ctx.db.add_to_playlist(pid, fp)
            self._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {label[:48]} ({len(fps)} temas)", "success")
            self._record_playlist_created(pid, label[:64], len(fps))

    def create_from_artist(self):
        all_items = self._all_library_tracks()
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
                pid = self._ctx.db.create_playlist(name)
                for fp in fps:
                    self._ctx.db.add_to_playlist(pid, fp)
                self._ctx.rebuild_sidebar()
                self._toast(f"Playlist creada: {name} ({len(fps)} temas)", "success")
                self._record_playlist_created(pid, name, len(fps))

    def create_from_genre(self):
        all_items = self._all_library_tracks()
        if not all_items:
            self._toast("No hay música en la biblioteca", "info")
            return
        genres = sorted(set(i.genre for i in all_items if i.genre))
        if not genres:
            self._toast("No se encontraron géneros", "info")
            return
        genre, ok = QInputDialog.getItem(
            self._win, "Crear playlist desde genero",
            "Selecciona:", genres, 0, False)
        if not ok or not genre:
            return
        tracks = [i for i in all_items if i.genre == genre]
        fps = [t.filepath for t in tracks if os.path.isfile(t.filepath)]
        if fps:
            pid = self._ctx.db.create_playlist(genre)
            for fp in fps:
                self._ctx.db.add_to_playlist(pid, fp)
            self._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {genre} ({len(fps)} temas)", "success")
            self._record_playlist_created(pid, genre, len(fps))

    def create_from_search(self):
        model = self._ctx.model
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
            pid = self._ctx.db.create_playlist(name)
            for fp in fps:
                self._ctx.db.add_to_playlist(pid, fp)
            self._ctx.rebuild_sidebar()
            self._toast(f"Playlist creada: {name} ({len(fps)} temas)", "success")
            self._record_playlist_created(pid, name, len(fps))

    def open_smart_playlist(self, key: str):
        self._ctx.navigate_sidebar(
            f"mix_{key}" if not key.startswith("mix_") else key)

    def hub_playlist_play(self, pid: int):
        items = self._ctx.db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        playback = self._svc.playback if self._svc and hasattr(self._svc, 'playback') else self._ctx.playback
        if hasattr(playback, 'play_queue'):
            playback.play_queue(fps)
        else:
            playback.enqueue(fps, play_now=True)
        self._toast("Reproduciendo playlist", "success")
        pl = self.get_playlist_by_id(pid)
        name = pl.get("name", "") if pl else ""
        self._select_playlist(pid, name)
        ctx = self._context()
        if ctx:
            ctx.record_playlist_played(playlist_id=pid, name=name, count=len(fps))
            ctx.record_queue_updated(count=len(fps), source="playlist")

    def hub_playlist_queue(self, pid: int):
        items = self._ctx.db.get_playlist_items(pid)
        fps = [i.filepath for i in items]
        self._ctx.playback.enqueue(fps, play_now=False)
        self._toast("Playlist anadida a la cola", "success")

        pl = self.get_playlist_by_id(pid)
        name = pl.get("name", "") if pl else ""
        self._select_playlist(pid, name)
        ctx = self._context()
        if ctx:
            ctx.record_playlist_queued(playlist_id=pid, name=name, count=len(fps))
            ctx.record_queue_updated(count=len(fps), source="playlist")

    # ── CRUD helpers ──

    def get_all_playlists(self) -> list[dict]:
        """Return all playlists from the database."""
        return self._ctx.db.get_playlists()

    def get_playlist_items(self, pid: int) -> list:
        """Return all tracks in a playlist."""
        return self._ctx.db.get_playlist_items(pid)

    def get_playlist_by_id(self, pid: int) -> dict | None:
        """Return a single playlist dict by id, or None."""
        return next(
            (p for p in self._ctx.db.get_playlists() if p["id"] == pid),
            None,
        )

    def create_playlist(self, name: str) -> int:
        pid = self._ctx.db.create_playlist(name.strip())
        self._ctx.rebuild_sidebar()
        self._record_playlist_created(pid, name.strip(), 0)
        return pid

    def delete_playlist(self, pid: int):
        pl = self.get_playlist_by_id(pid)
        name = pl.get("name", "") if pl else ""
        self._ctx.db.delete_playlist(pid)
        self._ctx.rebuild_sidebar()
        self._ctx.load_library()
        ctx = self._context()
        if ctx:
            ctx.record_playlist_deleted(playlist_id=pid, name=name)
        self._toast("Playlist eliminada.", "info")

    def add_track_to_playlist(self, pid: int, fp: str):
        self._ctx.db.add_to_playlist(pid, fp)
        ctx = self._context()
        if ctx:
            pl = self.get_playlist_by_id(pid)
            name = pl.get("name", "") if pl else ""
            ctx.record_track_added_to_playlist(playlist_id=pid, name=name, count=1)

    def create_playlist_from_tracks(self, tracks: list, name: str) -> int:
        if not tracks or not name:
            return 0
        pid = self._ctx.db.create_playlist(name.strip())
        valid_count = 0
        for t in tracks:
            fp = t.filepath if hasattr(t, 'filepath') else str(t)
            if os.path.isfile(fp):
                self._ctx.db.add_to_playlist(pid, fp)
                valid_count += 1
        self._ctx.rebuild_sidebar()
        self._toast(f"Playlist creada: {name[:48]} ({valid_count} temas)", "success")
        self._record_playlist_created(pid, name.strip(), valid_count)
        return pid

    def add_files_to_playlist_dialog(self, filepaths: list[str]):
        """Show dialog to add files to an existing playlist or create a new one."""
        if not filepaths:
            return
        from PySide6.QtWidgets import QInputDialog
        playlists = self._ctx.db.get_playlists()
        names = [p["name"] for p in playlists] + ["+ Nueva playlist"]
        name, ok = QInputDialog.getItem(
            self._win, "Agregar a playlist", "Selecciona playlist:",
            names, 0, False)
        if not ok:
            return
        if name == "+ Nueva playlist":
            name, ok = QInputDialog.getText(
                self._win, "Nueva playlist", "Nombre:")
            if not ok or not name.strip():
                return
            pid = self._ctx.db.create_playlist(name.strip())
        else:
            pl = next((p for p in playlists if p["name"] == name), None)
            if not pl:
                return
            pid = pl["id"]
        count = self._add_files_to_playlist(self._ctx.db, pid, filepaths)
        self._ctx.rebuild_sidebar()
        self._toast(f"Agregados {count} temas a '{name}'", "success")
        ctx = self._context()
        if ctx:
            ctx.record_track_added_to_playlist(playlist_id=pid, name=name, count=count)

    @staticmethod
    def _add_files_to_playlist(db, pid: int, filepaths: list[str]) -> int:
        """Pure logic: add valid files to a playlist. Returns count of added files."""
        import os
        valid = 0
        for fp in filepaths:
            if os.path.isfile(fp):
                db.add_to_playlist(pid, fp)
                valid += 1
        return valid

    def metadata_saved(self, filepaths: list):
        self._toast(f"Metadatos guardados en {len(filepaths)} archivos", "success")

    def refresh_library(self):
        self._ctx.load_library()

    # ── DB read accessors (non-playlist queries) ──

    def get_favorites(self) -> list[str]:
        """Return list of favorite filepaths from the database."""
        return self._ctx.db.get_favorites()

    def get_play_history(self, limit: int = 50) -> list[dict]:
        """Return recent play history entries from the database."""
        return self._ctx.db.get_play_history(limit=limit)

    def get_all_tracks(self) -> list:
        """Return all MediaItem track objects from the library."""
        return self._ctx.db.get_all()

    def save_queue(self, engine):
        """Persist current playback queue to the database for session restore."""
        try:
            if hasattr(engine, '_queue') and engine._queue:
                self._ctx.db.save_queue(engine._queue, engine._queue_index)
        except Exception:
            pass

    def add_files(self, filepaths: list[str]):
        """Add files to the library database. Each filepath is indexed."""
        for fp in filepaths:
            self._ctx.db.add_file(fp)

    def show_playlist_hub(self, key: str = ""):
        """Load and display the playlist hub page."""
        w = self._win
        pls = w._db.get_playlists()
        w._playlist_hub.set_playlists(pls)
        w._fade_content("playlist_hub")

    def show_playlist_detail(self, key: str):
        """Load and display a specific playlist detail view."""
        w = self._win
        pid = int(key.split(":", 1)[1])
        w._current_playlist = pid
        items = w._db.get_playlist_items(pid)
        pl = next((p for p in w._db.get_playlists() if p["id"] == pid), {"name": "Playlist"})
        w._playlist_detail.set_playlist(pl, items)
        total_dur = int(sum(getattr(i, 'duration', 0) or 0 for i in items))
        h = total_dur // 3600
        m = (total_dur % 3600) // 60
        dur_str = f"{h} h {m} min" if h > 0 else f"{m} min" if m > 0 else ""
        subtitle = f"{len(items)} canciones"
        if dur_str:
            subtitle += f" · {dur_str}"
        w._section_title.setText(pl.get("name", "Playlist"))
        w._section_subtitle.setText(subtitle)
        w._search.show()
        w._fade_content("playlist_detail")

    def on_playlist_track_activated(self, row: int, filepath: str):
        """Play entire playlist starting from the clicked track."""
        w = self._win
        pid = getattr(w, '_current_playlist', 0)
        if not pid:
            return
        items = w._db.get_playlist_items(pid)
        paths = [i.filepath for i in items if getattr(i, 'filepath', '')]
        if not paths:
            return
        start_idx = max(0, min(row, len(paths) - 1))
        if hasattr(w._playback, 'play_queue'):
            w._playback.play_queue(paths, start_idx)

    def update_playlist(self, pid: int, **kwargs):
        """Update playlist metadata (name, description, cover_path, cover_type)."""
        self._ctx.db.update_playlist(pid, **kwargs)

    def get_detected_tracks(self, limit: int = 100) -> list:
        """Return recently detected/identified tracks."""
        return self._ctx.db.get_detected_tracks(limit)

    def clear_detected_tracks(self):
        """Remove all detected track records."""
        self._ctx.db.clear_detected_tracks()

    def delete_detected_track(self, idx: int):
        """Delete a single detected track by its row index."""
        if hasattr(self._ctx.db, 'delete_detected_track'):
            self._ctx.db.delete_detected_track(idx)
