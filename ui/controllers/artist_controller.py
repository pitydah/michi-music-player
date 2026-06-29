"""Artist controller — artist grid and detail navigation logic."""
import os



class ArtistController:
    def __init__(self, window, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def show_artists_view(self, mode: str):
        self._ctx.artist_grid.set_view_mode(mode)
        self._ctx.show_library_hub()
        self._ctx.set_library_tab("artists")
        self._ctx.set_artist_stack(0)

    def open_artist_detail(self, artist_key: str):
        self._win._nav_ctrl.checkpoint()
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        repo.current_key = artist_key
        self._ctx.artist_detail.set_artist(group)

        self._ctx.section_title.setText(group.display_name)
        parts = [f"{group.album_count} álbumes", f"{group.track_count} canciones"]
        if group.total_duration:
            s = int(group.total_duration)
            parts.append(
                f"{s // 3600} h {(s % 3600) // 60} min" if s >= 3600
                else f"{s // 60} min")
        self._ctx.section_subtitle.setText(" · ".join(parts))
        self._ctx.view_switcher.set_available_modes([])
        self._ctx.set_artist_stack(1)
        self._ctx.fade_to("library_hub")

        ctx = getattr(self._win, '_context_svc', None)
        if ctx:
            ctx.update_selection(artist=group.display_name)

    def show_artists_overview(self):
        self._ctx.artist_repo.clear_current()
        self._ctx.configure_header("artists")
        self.show_artists_view(self._ctx.view_mode)

    def artist_filepaths(self, artist_key: str) -> list[str]:
        return self._ctx.artist_repo.filepaths(artist_key)

    def play_artist(self, artist_key: str, shuffle: bool = False):
        fps = self.artist_filepaths(artist_key)
        if fps:
            if shuffle:
                import random
                random.shuffle(fps)
            self._ctx.play_filepaths(fps, play_now=True)

    def queue_artist(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            self._ctx.playback.enqueue(fps, play_now=False)

    def _get_db(self):
        """Return database handle, preferring injected service."""
        if self._svc and hasattr(self._svc, 'db'):
            return self._svc.db
        return self._ctx.db

    def create_playlist_from_artist(self, artist_key: str):
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        db = self._get_db()
        pid = db.create_playlist(group.display_name)
        for fp in [t.filepath for t in group.all_tracks if os.path.isfile(t.filepath)]:
            db.add_to_playlist(pid, fp)
        self._ctx.rebuild_sidebar()
        self._ctx.toast.show(f"Playlist creada: {group.display_name}", "success")

    def edit_artist_metadata(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            self.open_metadata_for_files(fps)

    def open_metadata_for_files(self, filepaths: list[str]):
        self._ctx.metadata_editor.load_files(filepaths)
        self._ctx.configure_header("metadata_editor")
        self._ctx.fade_to("metadata_editor")

    def refresh_artist_info(self, artist_key: str):
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group or not hasattr(self._win, '_artist_enrich'):
            return
        if hasattr(repo, 'mark_enrichment_loading'):
            repo.mark_enrichment_loading(artist_key)
        self._win._artist_enrich.refresh_artist(artist_key)
        self._win._artist_enrich.enrich_artist(group, force=True)
        if hasattr(self._win._artist_grid, 'set_artists'):
            self._win._artist_grid.set_artists(repo.groups)
        self._ctx.toast.show(
            f"Actualizando info de {group.display_name}...", "info")

    def on_artist_enriched(self, artist_key: str, info):
        repo = self._ctx.artist_repo
        if hasattr(repo, 'apply_external_info'):
            repo.apply_external_info(artist_key, info)

        w = self._win
        if (hasattr(w, '_artist_detail') and hasattr(w._artist_detail, '_artist')
                and w._artist_detail._artist
                and w._artist_detail._artist.key == artist_key):
            group = repo.get_group(artist_key)
            if group:
                w._artist_detail.set_artist(group)
            else:
                w._artist_detail.set_external_info(info)

        if hasattr(w._artist_grid, 'set_artists'):
            w._artist_grid.set_artists(repo.groups)

    def on_artist_image_loaded(self, artist_key: str, local_path: str):
        repo = self._ctx.artist_repo
        w = self._win
        if hasattr(w._artist_grid, 'set_artists'):
            w._artist_grid.set_artists(repo.groups)
        if (hasattr(w, '_artist_detail') and hasattr(w._artist_detail, '_artist')
                and w._artist_detail._artist
                and w._artist_detail._artist.key == artist_key):
            group = repo.get_group(artist_key)
            if group:
                w._artist_detail.set_artist(group)

    def on_artist_enrichment_failed(self, artist_key: str, error: str):
        repo = self._ctx.artist_repo
        if hasattr(repo, 'mark_enrichment_error'):
            repo.mark_enrichment_error(artist_key, error)
        if hasattr(self._win._artist_grid, 'set_artists'):
            self._win._artist_grid.set_artists(repo.groups)
        self._ctx.toast.show(f"Enriquecimiento: {error}", "error")
