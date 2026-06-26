"""Genre Controller — genre navigation and actions."""
import os


class GenreController:
    def __init__(self, window, services=None, genre_repo=None,
                 genre_grid=None, genre_detail=None, metadata_editor=None):
        self._win = window  # backward compat
        self._svc = services
        self._repo = genre_repo or (services.genre_repo if services else None)
        self._grid = genre_grid or (services.genre_grid if services and hasattr(services, 'genre_grid') else None)
        self._detail = genre_detail
        self._metadata_editor = metadata_editor

    @property
    def _genre_repo(self):
        return self._repo or self._win._ctx.genre_repo

    @property
    def _genre_grid(self):
        return self._grid or self._win._ctx.genre_grid

    @property
    def _genre_detail(self):
        return self._detail or self._win._ctx.genre_detail

    @property
    def _meta_editor(self):
        return self._metadata_editor or self._win._ctx.metadata_editor

    def _ctx_or_svc(self, attr, default=None):
        """Unified access: try AppServices first, fall back to AppContext."""
        if self._svc and hasattr(self._svc, attr):
            return getattr(self._svc, attr)
        ctx = getattr(self._win, '_ctx', None)
        return getattr(ctx, attr, default) if ctx else default

    def show_genres_overview(self, mode: str = "grid"):
        repo = self._genre_repo
        repo.build(self._ctx_or_svc("all_items", []))
        self._genre_grid.set_genres(repo.groups, repo.families)
        self._ctx_or_svc("configure_header", lambda k: None)("genres")
        self._win._show_library_hub_page()
        if self._win._library_hub_page:
            self._win._library_hub_page.set_current_section("genres")
            self._win._genres_stack.setCurrentIndex(0)

    def open_genre_detail(self, genre_key: str):
        repo = self._genre_repo
        g = repo.get_group(genre_key)
        if not g:
            return
        repo.current_key = genre_key
        self._genre_detail.set_genre(g)
        ctx = getattr(self._win, '_ctx', None)
        if ctx:
            ctx.section_title.setText(g.name)
            parts = [f"{g.track_count} canciones", f"{g.artist_count} artistas",
                     f"{g.album_count} álbumes"]
            ctx.section_subtitle.setText(" · ".join(parts))
            ctx.view_switcher.set_available_modes([])
            self._win._genres_stack.setCurrentIndex(1)
            self._win._fade_content("library_hub")

    def back_to_overview(self):
        self._genre_repo.current_key = None
        self.show_genres_overview()

    def play_genre(self, genre_key: str, shuffle: bool = False):
        fps = self._genre_repo.filepaths_for_genre(genre_key)
        if fps:
            if shuffle:
                import random
                random.shuffle(fps)
            self._win._play_filepaths(fps, play_now=True)

    def queue_genre(self, genre_key: str):
        fps = self._genre_repo.filepaths_for_genre(genre_key)
        if fps:
            self._ctx_or_svc("playback").enqueue(fps, play_now=False)

    def create_playlist_from_genre(self, genre_key: str):
        g = self._genre_repo.get_group(genre_key)
        if not g:
            return
        db = self._ctx_or_svc("db")
        pid = db.create_playlist(g.name)
        for fp in [t.filepath for t in g.tracks if os.path.isfile(t.filepath)]:
            db.add_to_playlist(pid, fp)
        self._ctx_or_svc("rebuild_sidebar", lambda: None)()
        self._ctx_or_svc("toast", None).show(f"Playlist creada: {g.name}", "success")

    def edit_genre_metadata(self, genre_key: str):
        fps = self._genre_repo.filepaths_for_genre(genre_key)
        if fps:
            self._meta_editor.load_files(fps)
            self._ctx_or_svc("configure_header", lambda k: None)("metadata_editor")
            self._ctx_or_svc("fade_to", lambda k: None)("metadata_editor")

    def normalize_genre(self, genre_key: str):
        g = self._genre_repo.get_group(genre_key)
        if not g:
            return
        toast = self._ctx_or_svc("toast", None)
        if toast:
            toast.show(f"Normalización de '{g.name}': usa el Editor de metadatos para limpiar tags", "info")
        self.edit_genre_metadata(genre_key)
