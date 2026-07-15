"""Artist controller — artist grid and detail navigation logic."""
import os
import random



class ArtistController:
    def __init__(self, window, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    @property
    def _context_svc(self):
        return (
            getattr(self._svc, "context_svc", None)
            or getattr(self._ctx, "context_svc", None)
            or getattr(self._win, "_context_svc", None)
        )

    # ── Navigation ──

    def show_artists_view(self, mode: str):
        self._ctx.artist_grid.set_view_mode(mode)
        self._ctx.show_library_hub()
        self._ctx.set_library_tab("artists")
        self._ctx.set_artist_stack(0)

    def open_artist_detail(self, artist_key: str):
        if not getattr(self._win._nav_ctrl, 'is_restoring', False):
            self._win._nav_ctrl.checkpoint()
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        repo.current_key = artist_key
        insight = repo.insight_for_artist(artist_key)
        self._ctx.artist_detail.set_artist(group, insight)

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

        ctx = self._context_svc
        if ctx:
            ctx.update_selection(
                scope="artist",
                artist=group.display_name,
                album="",
                genre="",
                playlist_id=None,
                playlist_name="",
                folder_name="",
                mix_key="",
                search_query="",
            )

        if not getattr(self._win._nav_ctrl, 'is_restoring', False):
            self._win._nav_ctrl.force_push(f"artist:{artist_key}")

    def show_artists_overview(self):
        self._ctx.artist_repo.clear_current()
        self._ctx.configure_header("artists")
        self.show_artists_view(self._ctx.view_mode)

    # ── File helpers ──

    def artist_filepaths(self, artist_key: str) -> list[str]:
        return self._ctx.artist_repo.filepaths(artist_key)

    # ── Playback ──

    def play_artist(self, artist_key: str, shuffle: bool = False):
        fps = self.artist_filepaths(artist_key)
        if fps:
            if shuffle:
                random.shuffle(fps)
            self._ctx.play_filepaths(fps, play_now=True)

    def queue_artist(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            pc = getattr(self._win, "_playback_ctrl", None)
            if pc:
                pc.enqueue_with_context(fps, play_now=False, source="artist")
            else:
                self._ctx.playback.enqueue(fps, play_now=False)

    # ── DB ──

    def _get_db(self):
        if self._svc and hasattr(self._svc, 'db'):
            return self._svc.db
        return self._ctx.db

    # ── Playlist ──

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

    # ── Metadata ──

    def edit_artist_metadata(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if fps:
            self.open_metadata_for_files(fps)

    def open_metadata_for_files(self, filepaths: list[str]):
        self._ctx.metadata_editor.load_files(filepaths)
        self._ctx.configure_header("metadata_editor")
        self._ctx.fade_to("metadata_editor")

    # ── Enrichment ──

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
        repo.invalidate_insights()

        w = self._win
        if (hasattr(w, '_artist_detail') and hasattr(w._artist_detail, '_artist')
                and w._artist_detail._artist
                and w._artist_detail._artist.key == artist_key):
            group = repo.get_group(artist_key)
            if group:
                insight = repo.insight_for_artist(artist_key)
                w._artist_detail.set_artist(group, insight)
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
                insight = repo.insight_for_artist(artist_key)
                w._artist_detail.set_artist(group, insight)

    def on_artist_enrichment_failed(self, artist_key: str, error: str):
        repo = self._ctx.artist_repo
        if hasattr(repo, 'mark_enrichment_error'):
            repo.mark_enrichment_error(artist_key, error)
        if hasattr(self._win._artist_grid, 'set_artists'):
            self._win._artist_grid.set_artists(repo.groups)
        self._ctx.toast.show(f"Enriquecimiento: {error}", "error")

    # ── Mix ──

    def create_artist_mix(self, artist_key: str):
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        top_tracks = repo.top_tracks_for_artist(artist_key, 15)
        all_tracks = group.all_tracks

        if not top_tracks:
            self._ctx.toast.show(f"No hay canciones para crear mix de {group.display_name}", "warning")
            return

        import random as _random
        mix = []
        used = set()

        for t in top_tracks:
            if t.filepath not in used:
                mix.append(t.filepath)
                used.add(t.filepath)

        less_played = [t for t in all_tracks if t.filepath not in used
                       and (getattr(t, 'play_count', 0) or 0) < 3]
        _random.shuffle(less_played)
        for t in less_played[:int(len(top_tracks) * 0.75)]:
            if t.filepath not in used:
                mix.append(t.filepath)
                used.add(t.filepath)

        remaining = [t for t in all_tracks if t.filepath not in used]
        _random.shuffle(remaining)
        for t in remaining[:int(len(top_tracks) * 0.5)]:
            if t.filepath not in used:
                mix.append(t.filepath)
                used.add(t.filepath)

        mix_name = f"Mix - {group.display_name}"

        db = self._get_db()
        existing = db.get_playlist_by_name(mix_name)
        if existing:
            db.clear_playlist(existing)
            pid = existing
        else:
            pid = db.create_playlist(mix_name)

        for fp in mix:
            db.add_to_playlist(pid, fp)

        self._ctx.rebuild_sidebar()
        self._ctx.toast.show(f"Mix creado: {mix_name} ({len(mix)} canciones)", "success")

    # ── Analysis ──

    def analyze_artist_discography(self, artist_key: str):
        fps = self.artist_filepaths(artist_key)
        if not fps:
            self._ctx.toast.show("No hay archivos para analizar", "warning")
            return

        w = self._win
        if hasattr(w, '_audio_analysis') and w._audio_analysis:
            try:
                w._audio_analysis.analyze_files(fps)
                self._ctx.toast.show(
                    f"Analizando {len(fps)} canciones en Audio Lab...", "info")
                self._ctx.configure_header("audio_lab")
                self._ctx.fade_to("audio_lab")
                return
            except Exception:
                pass

        repo = self._ctx.artist_repo
        insight = repo.insight_for_artist(artist_key)
        if insight:
            q = insight.quality
            self._ctx.toast.show(
                f"{len(fps)} canciones · {q.lossless_count} lossless · "
                f"{q.hi_res_count} hi-res · {q.dominant_format}", "info")
        else:
            self._ctx.toast.show(f"{len(fps)} canciones listas para análisis", "info")

    # ── Micro Server ──

    def send_artist_to_micro_server(self, artist_key: str):
        try:
            from integrations.michi_link.services import (
                ImportToServerService, MicroServerService)
        except ImportError:
            self._ctx.toast.show("Michi Link no está disponible", "error")
            return

        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        fps = self.artist_filepaths(artist_key)
        if not fps:
            self._ctx.toast.show("No hay archivos para enviar", "warning")
            return

        micro_svc = getattr(self._win, '_micro_server_svc', None)
        if not micro_svc:
            try:
                micro_svc = MicroServerService()
                if not micro_svc.is_connected():
                    self._ctx.toast.show(
                        "No hay Michi Micro Server emparejado. "
                        "Abre Conexiones > Michi Link para emparejar un servidor.", "warning")
                    return
            except Exception:
                self._ctx.toast.show(
                    "No hay Michi Micro Server emparejado. "
                    "Abre Conexiones > Michi Link para emparejar un servidor.", "warning")
                return

        try:
            import_svc = ImportToServerService()
            session = import_svc.create_session(group.display_name)
            for fp in fps:
                session.add_file(fp)
            session.preflight()
            session.commit()
            self._ctx.toast.show(
                f"Enviado {group.display_name} a Micro Server "
                f"({len(fps)} canciones)", "success")
        except Exception as e:
            self._ctx.toast.show(f"Error al enviar a Micro Server: {e}", "error")

    # ── Mobile sync ──

    def sync_artist_to_mobile(self, artist_key: str):
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        fps = self.artist_filepaths(artist_key)
        if not fps:
            self._ctx.toast.show("No hay archivos para sincronizar", "warning")
            return
        w = self._win
        sync_mgr = getattr(w, '_sync_manager', None)
        if not sync_mgr:
            self._ctx.toast.show(
                "Sync móvil no disponible. Abre Conexiones > Michi Link para configurar.",
                "warning")
            return
        try:
            sync_mgr.set_manifest_provider(lambda: [
                {"filepath": fp, "size": os.path.getsize(fp)}
                for fp in fps if os.path.isfile(fp)
            ])
            if not sync_mgr.is_running:
                sync_mgr.start()
            self._ctx.toast.show(
                f"Preparando sincronización de {group.display_name} "
                f"({len(fps)} canciones)...", "info")
        except Exception as e:
            self._ctx.toast.show(f"Error al sincronizar: {e}", "error")

    # ── Alias resolution ──

    def resolve_artist_aliases(self, artist_key: str):
        from library.artist_aliases import (
            find_artist_alias_candidates, add_alias)
        repo = self._ctx.artist_repo
        group = repo.get_group(artist_key)
        if not group:
            return
        candidates = find_artist_alias_candidates(repo.groups)
        relevant = [(k1, k2, s) for k1, k2, s in candidates
                    if k1 == artist_key or k2 == artist_key]
        if not relevant:
            self._ctx.toast.show(
                f"No se encontraron duplicados para {group.display_name}", "info")
            return

        try:
            self._open_alias_dialog(artist_key, relevant)
        except Exception:
            for k1, k2, _score in relevant:
                target = k2 if k1 == artist_key else k1
                add_alias(artist_key, target)
            repo.build(repo._all_items if hasattr(repo, '_all_items') else [])
            repo.invalidate_insights()
            if hasattr(self._win._artist_grid, 'set_artists'):
                self._win._artist_grid.set_artists(repo.groups)
            self._ctx.toast.show(
                f"Alias resueltos para {group.display_name}", "success")

    def _open_alias_dialog(self, artist_key: str, candidates: list):
        try:
            from ui.dialogs.alias_resolution_dialog import AliasResolutionDialog
            repo = self._ctx.artist_repo
            group = repo.get_group(artist_key)
            if not group:
                return
            dialog = AliasResolutionDialog(
                group.display_name, candidates,
                lambda k: repo.get_group(k), self._win)
            if dialog.exec() == dialog.Accepted:
                target = dialog.selected_key()
                if target:
                    from library.artist_aliases import add_alias
                    add_alias(artist_key, target)
                    repo.build(repo._all_items if hasattr(repo, '_all_items') else [])
                    repo.invalidate_insights()
                    if hasattr(self._win._artist_grid, 'set_artists'):
                        self._win._artist_grid.set_artists(repo.groups)
                    self._ctx.toast.show("Alias resuelto correctamente", "success")
        except Exception:
            pass

    # ── Album/track actions ──

    def analyze_artist_album(self, filepaths: list[str]):
        w = self._win
        if hasattr(w, '_audio_analysis') and w._audio_analysis:
            try:
                w._audio_analysis.analyze_files(filepaths)
                self._ctx.toast.show(
                    f"Analizando {len(filepaths)} canciones...", "info")
                self._ctx.configure_header("audio_lab")
                self._ctx.fade_to("audio_lab")
                return
            except Exception:
                pass
        self._ctx.toast.show(f"{len(filepaths)} canciones listas para análisis", "info")

    def send_artist_album_to_micro_server(self, filepaths: list[str]):
        if not filepaths:
            return
        try:
            from integrations.michi_link.services import ImportToServerService
        except ImportError:
            self._ctx.toast.show("Michi Link no está disponible", "error")
            return

        micro_svc = getattr(self._win, '_micro_server_svc', None)
        if not micro_svc:
            self._ctx.toast.show(
                "No hay Michi Micro Server emparejado.", "warning")
            return

        try:
            import_svc = ImportToServerService()
            session = import_svc.create_session("Álbum")
            for fp in filepaths:
                session.add_file(fp)
            session.commit()
            self._ctx.toast.show(
                f"Enviado álbum a Micro Server ({len(filepaths)} canciones)", "success")
        except Exception as e:
            self._ctx.toast.show(f"Error al enviar: {e}", "error")

    def analyze_artist_track(self, filepath: str):
        w = self._win
        if hasattr(w, '_audio_analysis') and w._audio_analysis:
            try:
                w._audio_analysis.analyze_files([filepath])
                self._ctx.toast.show("Analizando canción...", "info")
                self._ctx.configure_header("audio_lab")
                self._ctx.fade_to("audio_lab")
                return
            except Exception:
                pass
        self._ctx.toast.show("Canción lista para análisis", "info")

    def send_artist_track_to_micro_server(self, filepath: str):
        self.send_artist_album_to_micro_server([filepath])
