"""Album controller — advanced actions on albums: play, queue, metadata, covers, quality, server."""
from __future__ import annotations

import logging
import os

from PySide6.QtWidgets import QInputDialog, QLineEdit

from library.album_identity import detect_album_artist
import contextlib

logger = logging.getLogger("michi.album_controller")


class AlbumController:
    def __init__(self, window, refresh_grid=None, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services
        self._refresh_grid = refresh_grid or (lambda: None)

    @property
    def _context_svc(self):
        return (
            getattr(self._svc, "context_svc", None)
            or getattr(self._ctx, "context_svc", None)
            or getattr(self._win, "_context_svc", None)
        )

    def _toast(self, text: str, level: str = "info"):
        self._ctx.toast.show(text, level)

    def _playback(self):
        return getattr(self._win, "_playback", None) or getattr(self._ctx, "playback", None)

    def _playback_ctrl(self):
        return getattr(self._win, "_playback_ctrl", None)

    def _filepaths(self, tracks: list) -> list[str]:
        return [str(getattr(t, "filepath", "") or "") for t in tracks
                if str(getattr(t, "filepath", "") or "")]

    def play_album(self, tracks: list) -> None:
        fps = self._filepaths(tracks)
        if not fps:
            self._toast("No hay canciones para reproducir", "error")
            return
        w = self._win
        if hasattr(w, "_play_filepaths"):
            w._play_filepaths(fps, play_now=True)
        else:
            pb = self._playback()
            if pb:
                pb.enqueue(fps, play_now=True)
        self._toast(f"Reproduciendo {len(fps)} canciones", "info")
        ctx = self._context_svc
        if ctx and hasattr(ctx, "record_queue_updated"):
            with contextlib.suppress(Exception):
                ctx.record_queue_updated(count=len(fps), source="album")

    def queue_album(self, tracks: list) -> None:
        fps = self._filepaths(tracks)
        if not fps:
            self._toast("No hay canciones para encolar", "error")
            return
        pb = self._playback()
        if pb and hasattr(pb, "enqueue"):
            pb.enqueue(fps, play_now=False)
        else:
            pc = self._playback_ctrl()
            if pc and hasattr(pc, "enqueue_with_context"):
                pc.enqueue_with_context(fps, play_now=False, source="album")
        self._toast(f"{len(fps)} canciones añadidas a la cola", "info")
        ctx = self._context_svc
        if ctx and hasattr(ctx, "record_queue_updated"):
            with contextlib.suppress(Exception):
                ctx.record_queue_updated(count=len(fps), source="album")

    def play_next_album(self, tracks: list) -> None:
        fps = self._filepaths(tracks)
        if not fps:
            self._toast("No hay canciones", "error")
            return
        pb = self._playback()
        if pb and hasattr(pb, "enqueue_next"):
            queue = pb.get_queue() or []
            if queue:
                pb.enqueue_next(fps)
                self._toast(f"{len(fps)} canciones insertadas después de la actual", "info")
                return
        self.play_album(tracks)

    def create_playlist(self, fps: list) -> None:
        pc = self._playback_ctrl()
        if pc:
            pc.enqueue_with_context(fps, play_now=False, source="album")
        else:
            pb = self._playback()
            if pb:
                pb.enqueue(fps, play_now=False)
        self._toast("Álbum añadido a la cola", "success")

    def create_playlist_from_tracks(self, tracks: list, name: str = "") -> None:
        fps = self._filepaths(tracks)
        if not fps:
            self._toast("No hay canciones para crear playlist", "error")
            return
        if not name:
            album = str(getattr(tracks[0], "album", "") if tracks else "")
            artist = detect_album_artist(tracks)
            suggested = f"{album} — {artist}" if album and artist else "Nueva playlist"
            name, ok = QInputDialog.getText(
                self._win, "Crear playlist", "Nombre:", QLineEdit.Normal, suggested)
            if not ok or not name.strip():
                return
        db = getattr(self._win, "_db", None) or getattr(self._ctx, "db", None)
        if not db:
            self._toast("Base de datos no disponible", "error")
            return
        pid = db.create_playlist(name.strip())
        for fp in fps:
            if os.path.isfile(fp):
                db.add_to_playlist(pid, fp)
        if hasattr(self._win, "_rebuild_sidebar"):
            self._win._rebuild_sidebar()
        self._toast(f"Playlist '{name.strip()}' creada con {len(fps)} canciones", "success")
        ctx = self._context_svc
        if ctx and hasattr(ctx, "record_playlist_created"):
            with contextlib.suppress(Exception):
                ctx.record_playlist_created(0, name.strip(), len(fps))

    def edit_album_metadata(self, tracks: list) -> None:
        w = self._win
        fps = self._filepaths(tracks)
        if not fps:
            self._toast("No hay archivos para editar", "error")
            return
        editor = getattr(w, "_metadata_editor", None)
        if editor and hasattr(editor, "load_files"):
            editor.load_files(fps)
            if hasattr(w, "_configure_header_for_section"):
                w._configure_header_for_section("metadata_editor")
            if hasattr(w, "_fade_content"):
                w._fade_content("metadata_editor")
        else:
            self._toast("Editor de metadatos no disponible", "error")

    def search_or_change_cover(self, tracks: list) -> None:
        if not tracks:
            self._toast("No hay canciones en este álbum", "error")
            return
        d = os.path.dirname(str(getattr(tracks[0], "filepath", "") or "."))
        try:
            from library.artwork_cache import cache_cover
            from library.cover_art_service import CoverArtService
            cover_path = os.path.join(d, "cover.jpg")
            if os.path.isfile(cover_path):
                from PySide6.QtGui import QPixmap
                pix = QPixmap(cover_path)
                if not pix.isNull():
                    cache_cover(cover_path, pix, "large")
                self._toast("Carátula actualizada", "success")
                self._refresh_grid()
            elif CoverArtService.find_cover(str(getattr(tracks[0], "filepath", ""))):
                self._toast("Carátula encontrada", "success")
                self._refresh_grid()
            else:
                self._toast("No se encontró carátula local", "info")
        except Exception as e:
            self._toast(f"Error al buscar carátula: {e}", "error")

    def analyze_album_quality(self, tracks: list) -> None:
        if not tracks:
            self._toast("No hay canciones para analizar", "error")
            return
        self._toast("Analizando calidad...", "info")
        try:
            from library.album_quality_service import AlbumQualityService
            svc = AlbumQualityService()
            worker_mgr = getattr(self._win, "_workers", None)
            if not worker_mgr or not hasattr(worker_mgr, "run_task"):
                self._toast("Sistema de workers no disponible", "error")
                return

            def _analyze_worker():
                return svc.analyze_album(tracks)

            def _show_result(detail):
                if not detail:
                    self._toast("No se pudo analizar la calidad", "error")
                    return
                msg = (f"Calidad dominante: {detail.dominant_quality.upper()}\n"
                       f"Formato predominante: {detail.dominant_format or '—'}\n"
                       f"Resolución: {detail.dominant_sample_rate // 1000}.{detail.dominant_sample_rate % 1000} kHz"
                       f" / {detail.dominant_bit_depth}-bit\n"
                       f"Pistas analizadas: {detail.tracks_analyzed}/{detail.total_tracks}\n"
                       f"Hi-Res: {'Sí' if detail.has_hires else 'No'}\n"
                       f"Lossless: {'Sí' if detail.has_lossless else 'No'}\n"
                       f"Lossy: {'Sí' if detail.has_lossy else 'No'}\n"
                       f"DSD: {'Sí' if detail.has_dsd else 'No'}\n")
                if detail.warnings:
                    msg += "\nAdvertencias:\n" + "\n".join(f"• {w}" for w in detail.warnings)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self._win, "Análisis de calidad", msg)

            worker_mgr.run_task("album_quality", _analyze_worker, on_done=_show_result)
        except Exception as e:
            self._toast(f"Error al analizar calidad: {e}", "error")
        ctx = self._context_svc
        if ctx and hasattr(ctx, "record_audio_analysis_finished"):
            with contextlib.suppress(Exception):
                ctx.record_audio_analysis_finished({"track_count": len(tracks)})

    def send_album_to_server(self, tracks: list) -> None:
        try:
            from integrations.michi_link.services.import_to_server_service import (
                ImportToServerService,
            )
            svc = ImportToServerService()
            server = getattr(self._ctx, "micro_server", None)
            if not server:
                self._toast(
                    "Michi Link no está configurado. Configura un servidor en "
                    "Dispositivos > Michi Sync Suite.", "info")
                return
            fps = self._filepaths(tracks)
            if not fps:
                self._toast("No hay archivos para enviar", "error")
                return

            # Preflight
            session_result = svc.create_session(server, fps)
            if not session_result.ok:
                self._toast(f"Error al preparar envío: {session_result.message}", "error")
                return
            pd = session_result.data
            existing = pd.get("existing", 0)
            needs = pd.get("needs_upload", 0)

            # Dialog
            from ui.dialogs.album_server_import_dialog import AlbumServerImportDialog
            album_title = str(getattr(tracks[0], "album", "Álbum") if tracks else "Álbum")
            dlg = AlbumServerImportDialog(
                self._win, album_title, len(fps), existing, needs)
            if not dlg.exec() or not dlg.was_confirmed():
                sid = pd.get("session_id", "")
                if sid:
                    with contextlib.suppress(Exception):
                        svc.rollback(sid)
                return

            # Use AlbumImportWorker via WorkerManager
            from integrations.michi_link.services.album_import_worker import (
                AlbumImportWorker, AlbumImportProgress, AlbumImportResult,
            )
            worker_mgr = getattr(self._win, "_workers", None)
            if not worker_mgr or not hasattr(worker_mgr, "run_task"):
                self._toast("Sistema de workers no disponible", "error")
                return

            sid = pd.get("session_id", "")
            worker = AlbumImportWorker(
                server, fps, import_service=svc, session_id=sid)

            self._active_album_import_worker = worker

            def _on_progress(progress: AlbumImportProgress):
                dlg.set_progress(progress.current, progress.total)

            def _on_finished(result: AlbumImportResult):
                self._active_album_import_worker = None
                if result.ok:
                    AlbumServerImportDialog.show_report(
                        self._win, "Importación completada", result.message, is_error=False)
                else:
                    AlbumServerImportDialog.show_report(
                        self._win, "Importación fallida", result.message, is_error=True)

            def _on_failed(err: str):
                self._active_album_import_worker = None
                AlbumServerImportDialog.show_report(
                    self._win, "Error de importación", err, is_error=True)

            worker.progress.connect(_on_progress)
            worker.finished.connect(_on_finished)
            worker.failed.connect(_on_failed)

            worker_mgr.run_task("album_import", worker.run)
        except ImportError:
            self._toast("Michi Link no está disponible en esta versión", "info")

    def tracks_from_group(self, group) -> list:
        """Extract tracks list from a CoverFlowItem or AlbumGroup."""
        if hasattr(group, "data") and isinstance(group.data, dict):
            return group.data.get("tracks", [])
        if isinstance(group, list):
            return group
        return []

    def review_album_duplicates(self, tracks: list) -> None:
        """Find duplicate candidates for this album across the full library."""
        if not tracks:
            self._toast("No hay canciones para revisar duplicados", "error")
            return
        try:
            from library.album_repository import AlbumRepository
            from library.album_duplicate_service import AlbumDuplicateService
            w = self._win
            all_items = getattr(w, '_all_items', None)
            if not all_items:
                all_items = getattr(self._ctx, 'db', None)
                all_items = all_items.get_all() if all_items and hasattr(all_items, 'get_all') else []

            if not all_items:
                self._toast("Biblioteca no disponible para búsqueda de duplicados", "info")
                return

            repo = AlbumRepository()
            repo.build(all_items)

            from library.album_identity import compute_album_identity
            target_identity = compute_album_identity(tracks)
            target_key = target_identity.album_key

            svc = AlbumDuplicateService()
            all_groups = repo.list_groups()
            target_group = None
            for g in all_groups:
                if g.identity.album_key == target_key:
                    target_group = g
                    break
            if not target_group:
                self._toast("No se pudo identificar el álbum en la biblioteca", "error")
                return

            candidates = svc.find_for_group(all_groups, target_group)
            if candidates:
                msg_lines = [f"Posibles duplicados de: {target_group.identity.display_title} "
                             f"— {target_group.identity.display_artist}"]
                for c in candidates[:5]:
                    left_g = repo.get_group(c.left_key)
                    right_g = repo.get_group(c.right_key)
                    left_name = f"{left_g.identity.display_title} — {left_g.identity.display_artist}" if left_g else c.left_key[:8]
                    right_name = f"{right_g.identity.display_title} — {right_g.identity.display_artist}" if right_g else c.right_key[:8]
                    msg_lines.append(f"\n{left_name}")
                    msg_lines.append(f"vs {right_name}")
                    msg_lines.append(f"Confianza: {c.confidence:.0%} · Acción: {c.recommended_action}")
                    for r in c.reasons[:3]:
                        msg_lines.append(f"  • {r}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self._win, "Revisar duplicados", "\n".join(msg_lines))
            else:
                self._toast("No se encontraron duplicados de este álbum en la biblioteca", "info")
        except Exception as e:
            self._toast(f"Error al revisar duplicados: {e}", "error")

    def sync_album_to_mobile(self, tracks: list) -> None:
        self._toast("Disponible cuando Michi Sync Suite esté configurado", "info")

    def open_album_folder(self, tracks: list) -> None:
        for t in tracks:
            fp = str(getattr(t, "filepath", "") or "")
            if fp:
                folder = os.path.dirname(fp)
                if not os.path.isdir(folder):
                    self._toast("La carpeta no existe", "error")
                    return
                try:
                    from core.external_process import run_process
                    run_process(["xdg-open", folder])
                except Exception:
                    self._toast("No se pudo abrir la carpeta", "error")
                return
        self._toast("No se encontró la carpeta", "error")

    # Legacy methods

    def search_cover(self, group):
        tracks = group.data.get("tracks", []) if hasattr(group, "data") and group.data else []
        self.search_or_change_cover(tracks)

    def open_folder(self, folder: str):
        from core.external_process import run_process
        run_process(["xdg-open", folder])

    def show_details(self, group):
        tracks = group.data.get("tracks", []) if hasattr(group, "data") and group.data else []
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
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self._win, "Detalles del álbum", msg)

    def show_album_detail_from_cover_item(self, cover_item):
        w = self._win
        if not getattr(w._nav_ctrl, 'is_restoring', False):
            w._nav_ctrl.checkpoint()
        album = getattr(cover_item, 'title', '') or ''
        artist = getattr(cover_item, 'subtitle', '') or ''
        tracks = []
        data = getattr(cover_item, 'data', None) or {}
        if isinstance(data, dict):
            album_group = data.get("album_group")
            album_key = data.get("album_key", "")

            # Priority 1: direct album_group reference
            if album_group is not None:
                tracks = album_group.tracks
                album = album_group.identity.display_title
                artist = album_group.identity.display_artist

            # Priority 2: album_key from w._album_data_repo
            elif album_key and hasattr(w, "_album_data_repo"):
                repo = w._album_data_repo
                group = repo.get_group(album_key) if repo else None
                if group:
                    tracks = group.tracks
                    album = group.identity.display_title
                    artist = group.identity.display_artist

            # Priority 3: tracks from data dict
            if not tracks:
                tracks = data.get("tracks", [])

        # Fallback: search by normalized title (last resort, safe mode)
        if not tracks and hasattr(w, '_all_items'):
            import unicodedata
            from library.album_art import group_by_album
            def _norm(s):
                s = (s or '').strip().lower()
                return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
            exact = []
            partial = []
            for a, ar, tr in group_by_album(w._lib_ctrl.filtered_album_items()):
                if _norm(album) == _norm(a):
                    exact.append((a, ar, tr))
                elif album and _norm(album) in _norm(a):
                    partial.append((a, ar, tr))
            if exact:
                album, artist, tracks = exact[0]
            elif len(partial) == 1:
                album, artist, tracks = partial[0]
            elif len(partial) > 1:
                self._toast(
                    "Hay varios álbumes parecidos. "
                    "Abre el álbum desde el grid para evitar ambigüedad.", "info")
                w._count.setText("Selecciona un álbum")
                return
        if not tracks:
            w._count.setText("Selecciona un álbum")
            return
        dur = sum(getattr(t, 'duration', 0) or 0 for t in tracks)
        mins = int(dur // 60)
        dur_str = f"{mins // 60} h {mins % 60} min" if mins >= 60 else f"{mins} min"
        year = str(tracks[0].year) if tracks and getattr(tracks[0], 'year', 0) else ""
        exts = set((getattr(t, 'ext', '') or '').upper().lstrip(".") for t in tracks if getattr(t, 'ext', ''))
        fmt = " · ".join(sorted(exts)) if exts else ""

        # Build quality and health info
        quality_info = None
        health_info = None
        try:
            # Use album_group data if available
            if album_group is not None:
                g = [album_group]
            elif album_key and hasattr(w, "_album_data_repo"):
                g = [w._album_data_repo.get_group(album_key)] if w._album_data_repo.get_group(album_key) else []
            else:
                from library.album_repository import AlbumRepository
                repo = AlbumRepository()
                repo.build(tracks)
                g = repo.list_groups()
            group_obj = g[0] if g else None
            if group_obj and group_obj.quality:
                q = group_obj.quality
                q_parts = [f"Calidad: {q.dominant_quality.upper()}"]
                if q.dominant_sample_rate:
                    q_parts.append(f"{q.dominant_sample_rate // 1000}.{q.dominant_sample_rate % 1000} kHz")
                if q.dominant_bit_depth:
                    q_parts.append(f"{q.dominant_bit_depth}-bit")
                quality_info = " · ".join(q_parts)
            if group_obj and group_obj.health:
                h = group_obj.health
                h_parts = []
                if h.status == "warning":
                    h_parts.append("Requiere revisión")
                if h.missing_files:
                    h_parts.append(f"{h.missing_files} archivo(s) faltante(s)")
                if h.missing_titles:
                    h_parts.append(f"{h.missing_titles} pista(s) sin título")
                if not h.missing_files and h.status == "ok":
                    h_parts.append("OK")
                health_info = " · ".join(h_parts) if h_parts else None
        except Exception:
            pass

        w._album_detail_view.set_album(
            title=album, artist=artist, year=year,
            cover_pixmap=getattr(cover_item, 'pixmap', None),
            tracks=tracks, total_duration=dur_str, format_info=fmt,
            quality_info=quality_info, health_info=health_info)
        w._albums_stack.setCurrentIndex(1)

        ctx = self._context_svc
        if ctx:
            ctx.update_selection(
                scope="album",
                album=album,
                artist=artist,
                genre="",
                playlist_id=None,
                playlist_name="",
                folder_name="",
                mix_key="",
                search_query="",
            )
        w._count.setText(album)

        if album_key and not getattr(w._nav_ctrl, 'is_restoring', False):
            w._nav_ctrl.force_push(f"album:{album_key}")

    def navigate_to_album_by_title(self, album_title: str):
        w = self._win
        if not hasattr(w, '_all_items') or not w._all_items:
            return
        from collections import namedtuple
        FakeItem = namedtuple("FakeCoverItem", ["title", "subtitle", "pixmap", "data"])
        tracks = [
            t for t in w._all_items
            if (getattr(t, "album", "") or "").lower().strip() == album_title.lower().strip()
        ]
        if not tracks:
            tracks = [
                t for t in w._all_items
                if album_title.lower().strip() in (getattr(t, "album", "") or "").lower().strip()
            ]
        if not tracks:
            w._ctx.toast.show(f"Álbum \"{album_title}\" no encontrado", "warning")
            return
        artist = getattr(tracks[0], "artist", "") or getattr(tracks[0], "albumartist", "") or ""
        fake = FakeItem(
            title=album_title,
            subtitle=artist,
            pixmap=None,
            data={"tracks": tracks},
        )
        self.show_album_detail_from_cover_item(fake)
