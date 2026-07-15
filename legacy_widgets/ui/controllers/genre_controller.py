"""GenreController — genre navigation, actions, and integration with new services."""
import os
import logging
import random

_log = logging.getLogger("michi.genre_ctrl")


class GenreController:
    def __init__(self, window, services=None, genre_repo=None,
                 genre_grid=None, genre_detail=None, metadata_editor=None,
                 genre_hub_page=None, genre_detail_page=None,
                 genre_cleanup_page=None, genre_cleanup_ctrl=None,
                 genre_stats_service=None, genre_mix_service=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services
        self._repo = genre_repo or (services.genre_repo if services else None)
        self._grid = genre_grid
        self._detail = genre_detail
        self._metadata_editor = metadata_editor
        self._hub_page = genre_hub_page
        self._detail_page = genre_detail_page
        self._cleanup_page = genre_cleanup_page
        self._cleanup_ctrl = genre_cleanup_ctrl
        self._stats_svc = genre_stats_service
        self._mix_svc = genre_mix_service

        # DB-backed repos
        self._db_genre_repo = None

    def bind_pages(self, hub_page=None, detail_page=None, cleanup_page=None,
                   cleanup_ctrl=None, db_genre_repo=None, stats_svc=None,
                   mix_svc=None):
        if hub_page is not None:
            self._hub_page = hub_page
        if detail_page is not None:
            self._detail_page = detail_page
        if cleanup_page is not None:
            self._cleanup_page = cleanup_page
        if cleanup_ctrl is not None:
            self._cleanup_ctrl = cleanup_ctrl
        if db_genre_repo is not None:
            self._db_genre_repo = db_genre_repo
        if stats_svc is not None:
            self._stats_svc = stats_svc
        if mix_svc is not None:
            self._mix_svc = mix_svc

    @property
    def _context_svc(self):
        return (
            getattr(self._svc, "context_svc", None)
            or getattr(self._ctx, "context_svc", None)
            or getattr(self._win, "_context_svc", None)
        )

    @property
    def _genre_repo(self):
        return self._repo or self._ctx.genre_repo

    @property
    def _genre_grid(self):
        return self._grid or (self._ctx.genre_grid if hasattr(self._ctx, 'genre_grid') else None)

    @property
    def _meta_editor(self):
        return self._metadata_editor or (self._ctx.metadata_editor if hasattr(self._ctx, 'metadata_editor') else None)

    @property
    def _genre_detail(self):
        return self._detail or (self._ctx.genre_detail if hasattr(self._ctx, 'genre_detail') else None)

    def _ctx_or_svc(self, attr, default=None):
        if self._svc and hasattr(self._svc, attr):
            return getattr(self._svc, attr)
        return getattr(self._ctx, attr, default)

    def _db(self):
        return self._ctx_or_svc("db", None)

    # ── Hub navigation ──

    def show_genres_hub(self, mode: str = "hub"):
        if self._hub_page and self._stats_svc:
            try:
                self._stats_svc.invalidate()
                overview = self._stats_svc.get_genres_overview()
                health = self._stats_svc.get_health_summary()
                self._hub_page.set_genres(overview, health)
                self._hub_page.set_health_issues(
                    duplicates=health.get("duplicate_groups", 0),
                    junk=health.get("junk_values", 0),
                    rare=health.get("rare_genres", 0),
                )
                self._ctx_or_svc("configure_header", lambda k: None)("genres")
                self._ctx.show_library_hub()
                self._ctx.set_library_tab("genres")
                return
            except Exception as e:
                _log.warning("show_genres_hub failed: %s", e)
        self.show_genres_overview()

    # ── Legacy grid-based navigation (fallback) ──

    def show_genres_overview(self, mode: str = "grid"):
        repo = self._genre_repo
        db = self._db()
        all_items = db.get_all() if db else []
        repo.build(all_items)
        if self._genre_grid:
            self._genre_grid.set_genres(repo.groups, repo.families)
        self._ctx_or_svc("configure_header", lambda k: None)("genres")
        self._ctx.show_library_hub()
        self._ctx.set_library_tab("genres")
        self._ctx.set_genre_stack(0)

    # ── Detail navigation ──

    def open_genre_detail(self, genre_key: str):
        if not getattr(self._win._nav_ctrl, 'is_restoring', False):
            self._win._nav_ctrl.checkpoint()

        if self._detail_page and self._stats_svc:
            detail = self._stats_svc.get_genre_detail(genre_key)
            if detail:
                tracks = self._stats_svc.get_tracks_for_genre(genre_key)
                artists = list(set(getattr(t, 'artist', '') or '' for t in tracks if getattr(t, 'artist', '')))
                albums = list(set(getattr(t, 'album', '') or '' for t in tracks if getattr(t, 'album', '')))
                self._detail_page.set_genre(detail, tracks, artists=sorted(artists), albums=sorted(albums))
                self._ctx.section_title.setText(genre_key)
                subtitle = f"{detail.get('track_count', 0)} canciones"
                self._ctx.section_subtitle.setText(subtitle)
                self._ctx.view_switcher.set_available_modes([])
                self._ctx.fade_to("library_hub")
                ctx = self._context_svc
                if ctx:
                    ctx.update_selection(
                        scope="genre", genre=genre_key,
                        album="", artist="", playlist_id=None,
                        playlist_name="", folder_name="",
                        mix_key="", search_query="")
                return

        # Fallback to legacy detail
        repo = self._genre_repo
        g = repo.get_group(genre_key)
        if not g:
            return
        repo.current_key = genre_key
        detail = self._genre_detail
        if detail:
            detail.set_genre(g)
        self._ctx.section_title.setText(g.name)
        parts = [f"{g.track_count} canciones", f"{g.artist_count} artistas",
                 f"{g.album_count} álbumes"]
        self._ctx.section_subtitle.setText(" · ".join(parts))
        self._ctx.view_switcher.set_available_modes([])
        self._ctx.set_genre_stack(1)
        self._ctx.fade_to("library_hub")
        ctx = self._context_svc
        if ctx:
            ctx.update_selection(
                scope="genre", genre=g.name,
                album="", artist="", playlist_id=None,
                playlist_name="", folder_name="",
                mix_key="", search_query="")

        if not getattr(self._win._nav_ctrl, 'is_restoring', False):
            self._win._nav_ctrl.force_push(f"genre:{genre_key}")

    def back_to_overview(self):
        if self._genre_repo:
            self._genre_repo.current_key = None
        self.show_genres_hub()

    # ── Playback actions ──

    def play_genre(self, genre_key: str, shuffle: bool = False):
        fps = self._get_filepaths_for_genre(genre_key)
        if fps:
            if shuffle:
                random.shuffle(fps)
            playback = self._ctx_or_svc("playback", None)
            if playback and hasattr(playback, 'play_queue'):
                playback.play_queue(fps)
            elif playback:
                playback.enqueue(fps, play_now=True)

    def queue_genre(self, genre_key: str):
        fps = self._get_filepaths_for_genre(genre_key)
        if fps:
            pc = getattr(self._win, "_playback_ctrl", None)
            if pc:
                pc.enqueue_with_context(fps, play_now=False, source="genre")
            else:
                playback = self._ctx_or_svc("playback", None)
                if playback:
                    playback.enqueue(fps, play_now=False)

    def create_mix_for_genre(self, genre_key: str, mode: str = "all"):
        if self._mix_svc:
            tracks = self._mix_svc.create_mix(genre_key, mode=mode, limit=30)
            if tracks:
                fps = [getattr(t, 'filepath', '') for t in tracks if getattr(t, 'filepath', '')]
                if fps:
                    playback = self._ctx_or_svc("playback", None)
                    if playback and hasattr(playback, 'play_queue'):
                        playback.play_queue(fps)
                    elif playback:
                        playback.enqueue(fps, play_now=True)
                    self._show_toast(f"Mix de {genre_key} creado ({len(fps)} canciones)", "info")
                    return
        self._show_toast(f"No se pudo crear mix para {genre_key}", "warning")

    def create_radio_for_genre(self, genre_key: str):
        if self._mix_svc:
            queue = self._mix_svc.create_radio_queue(genre_key, initial_size=20)
            if queue:
                fps = [getattr(t, 'filepath', '') for t in queue if getattr(t, 'filepath', '')]
                playback = self._ctx_or_svc("playback", None)
                if playback and hasattr(playback, 'play_queue'):
                    playback.play_queue(fps)
                self._show_toast(f"Radio de {genre_key} iniciada", "success")
                return
        self._show_toast(f"No se pudo iniciar radio para {genre_key}", "warning")

    def create_playlist_from_genre(self, genre_key: str):
        db = self._db()
        if not db:
            return
        # Try DB-backed first
        tracks = []
        if self._stats_svc:
            tracks = self._stats_svc.get_tracks_for_genre(genre_key)
        if not tracks:
            g = self._genre_repo.get_group(genre_key)
            if g:
                tracks = g.tracks
        if not tracks:
            self._show_toast(f"No se encontraron canciones para {genre_key}", "warning")
            return
        pid = db.create_playlist(genre_key)
        for t in tracks:
            fp = getattr(t, 'filepath', '') or ''
            if fp and os.path.isfile(fp):
                db.add_to_playlist(pid, fp)
        self._ctx_or_svc("rebuild_sidebar", lambda: None)()
        self._show_toast(f"Playlist creada: {genre_key}", "success")

    def create_smart_playlist_from_genre(self, genre_key: str, rules: dict | None = None):
        if self._mix_svc:
            pid = self._mix_svc.create_smart_playlist(f"{genre_key} - Smart", genre_key, rules=rules)
            if pid:
                self._ctx_or_svc("rebuild_sidebar", lambda: None)()
                self._show_toast(f"Playlist inteligente creada: {genre_key}", "success")
                return
        self._show_toast(f"No se pudo crear playlist inteligente para {genre_key}", "warning")

    # ── Metadata actions ──

    def edit_genre_metadata(self, genre_key: str):
        fps = self._get_filepaths_for_genre(genre_key)
        if fps and self._meta_editor:
            self._meta_editor.load_files(fps)
            self._ctx_or_svc("configure_header", lambda k: None)("metadata_editor")
            self._ctx_or_svc("fade_to", lambda k: None)("metadata_editor")

    def normalize_genre(self, genre_key: str):
        if self._cleanup_ctrl:
            count = self._cleanup_ctrl.execute_rename(genre_key, genre_key)
            if count:
                self._show_toast(f"Género normalizado: {genre_key} ({count} tracks)", "success")
            else:
                self._show_toast(f"No se requirió normalización para {genre_key}", "info")
            # Add alias for future imports
            if self._db_genre_repo and count:
                self._db_genre_repo.add_alias(genre_key, genre_key, source="user")
        else:
            self._show_toast(
                f"Normalización de '{genre_key}': usa el Editor de metadatos para limpiar tags", "info")
            self.edit_genre_metadata(genre_key)

    def show_cleanup_page(self):
        if self._cleanup_page and self._cleanup_ctrl:
            self._cleanup_ctrl.set_page(self._cleanup_page)
            self._cleanup_ctrl.scan_and_show()
            self._ctx.section_title.setText("Limpieza de géneros")
            self._ctx.section_subtitle.setText("Normaliza estilos, detecta duplicados y corrige canciones sin género")
            self._ctx.view_switcher.set_available_modes([])
            self._ctx.fade_to("library_hub")

    # ── Helpers ──

    def _get_filepaths_for_genre(self, genre_key: str) -> list[str]:
        if self._stats_svc:
            tracks = self._stats_svc.get_tracks_for_genre(genre_key)
            fps = [getattr(t, 'filepath', '') for t in tracks
                   if getattr(t, 'filepath', '') and os.path.isfile(t.filepath)]
            if fps:
                return fps
        repo = self._genre_repo
        return repo.filepaths_for_genre(genre_key)

    def _show_toast(self, message: str, level: str = "info"):
        toast = self._ctx_or_svc("toast", None)
        if toast:
            toast.show(message, level)
