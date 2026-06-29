"""Playback controller — core track playback, table menus, EQ, state handling."""
import contextlib
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QDialog

from audio.player import PlaybackState
from sources.base_source import TrackRef
from library.trackref_model import TrackRefTableModel
from library.cover_art_service import CoverArtService


class PlaybackController:
    def __init__(self, window):
        self._win = window

    def on_table_menu(self, pos):
        idx = self._win._ctx.table.indexAt(pos)
        if not idx.isValid():
            return
        fp = self._win._ctx.model.index(idx.row(), TrackRefTableModel.COL_URI)
        fp = self._win._ctx.model.data(fp, Qt.DisplayRole)
        if not fp:
            return
        is_remote = fp.startswith("http://") or fp.startswith("https://")
        menu = QMenu(self._win)
        menu.addAction("Reproducir", lambda: self._win._ctx.play_file(fp))
        menu.addAction("Añadir a cola",
                       lambda: self._win._ctx.playback.enqueue([fp], play_now=False))

        # ── Add to playlist submenu ──
        pl_menu = menu.addMenu("Añadir a playlist")
        try:
            playlists = self._win._ctx.db.get_playlists()
            for pl in playlists:
                name = pl.get("name", "Sin nombre")
                pid = pl.get("id", 0)
                pl_menu.addAction(name[:40], lambda p=pid, f=fp: (
                    self._win._ctx.db.add_to_playlist(p, f),
                    self._win._ctx.rebuild_sidebar()))
            pl_menu.addSeparator()
        except Exception:
            pass
        pl_menu.addAction("+ Nueva playlist...",
                          lambda f=fp: self._add_to_new_playlist(f))

        menu.addSeparator()
        if is_remote:
            menu.addAction("Copiar URL", lambda: QApplication.clipboard().setText(fp))
        else:
            menu.addAction("Editar metadatos...", lambda: self.edit_tags(fp))
        menu.exec(self._win._ctx.table.viewport().mapToGlobal(pos))

    def _add_to_new_playlist(self, filepath: str):
        """Create a new playlist with the given track."""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self._win, "Nueva playlist", "Nombre de la playlist:")
        if not ok or not name.strip():
            return
        pid = self._win._ctx.db.create_playlist(name.strip())
        self._win._ctx.db.add_to_playlist(pid, filepath)
        self._win._ctx.rebuild_sidebar()

    def edit_tags(self, filepath: str):
        from library.tag_editor import TagEditorDialog
        dlg = TagEditorDialog(filepath, self._win)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._win._ctx.db.add_file(filepath)
            self._win._ctx.load_library()

    def on_table_dbl(self, idx):
        if self._win._ctx.current_section_key == "artists":
            artist_name = self._win._ctx.model.data(
                self._win._ctx.model.index(idx.row(), TrackRefTableModel.COL_TITLE),
                Qt.DisplayRole)
            if artist_name:
                items = self._win._ctx.db.search_advanced(f"artist:{artist_name}")
                refs = [TrackRef(uri=i.filepath,
                                 title=i.title or os.path.basename(i.filepath),
                                 artist=i.artist, album=i.album,
                                 duration=i.duration, year=i.year, genre=i.genre)
                        for i in items]
                self._win._ctx.model.populate(refs)
                self._win._ctx.section_subtitle.setText(
                    f"Todas las canciones de: {artist_name}")
                self._win._ctx.count.setText(f"{len(refs)} canciones")
                self._win._ctx.views.show("library")
                self.attach_track_table(self._win._ctx.table, self._win._ctx.model)
                self._win._ctx.table.setColumnWidth(0, 72)
                self._win._ctx.table.setColumnWidth(1, 260)
                self._win._ctx.table.setColumnWidth(2, 170)
                self._win._ctx.table.setColumnWidth(3, 170)
                self._win._ctx.table.setColumnWidth(4, 55)
                self._win._ctx.table.setColumnWidth(5, 110)
                self._win._ctx.table.setColumnWidth(6, 75)
            return

        track = self._win._ctx.model.get_trackref(idx.row())
        if track:
            self.play_trackref(track)

    def play_trackref(self, track: TrackRef):
        self._win._ctx.current_ref = track

        if track.uri.startswith("http"):
            self._win._ctx.playback.play_url(track.uri, track.title, track.artist)
        else:
            self._win._ctx.playback.enqueue([track.uri], play_now=True)

        name = track.title or os.path.basename(track.uri)
        artist = track.artist or ""
        quality_str = ""
        album = track.album or ""

        item = self._win._ctx.items_index.get(track.uri)
        if item:
            artist = item.artist or artist
            album = item.album or album
            ext = item.ext.upper().lstrip(".")
            if item.sample_rate:
                quality_str = (
                    f"{ext} \u00b7 {item.sample_rate / 1000:.1f}kHz"
                    if item.sample_rate >= 1000
                    else f"{ext} \u00b7 {item.sample_rate}Hz")
            elif item.bitrate and item.bitrate >= 1000:
                quality_str = f"{ext} \u00b7 {item.bitrate // 1000}kbps"
            elif item.ext:
                quality_str = ext

        if not quality_str:
            qual, _ = CoverArtService.quality_label(track.uri)
            quality_str = qual

        # Resolve cover + quality and update NowPlayingBar
        self._win._ctx.player_bar.set_track_from_ref(track)
        self._win._ctx.player_bar.set_quality(quality_str)

        # Quality classification (color-coded badge)
        from audio.quality_classifier import classify_audio_quality
        qc = classify_audio_quality(item) if item else {"category": "unknown", "label": quality_str, "tooltip": ""}
        self._win._ctx.player_bar.set_quality_info(
            qc.get("label", quality_str),
            qc.get("category", "unknown"),
            qc.get("tooltip", ""))

        # Audio route diagnostics for badge tooltip
        try:
            diag = self._win._ctx.player.get_audio_diagnostics() if hasattr(
                self._win._ctx.player, 'get_audio_diagnostics') else None
            if diag and hasattr(self._win, '_player_bar_ctrl') and self._win._player_bar_ctrl:
                self._win._player_bar_ctrl.set_route_tooltip(diag)
        except Exception:
            import logging
            logging.getLogger("michi.playback").debug("audio diagnostics not available")

        if track.uri.startswith("http") and track.cover_path:
            pix = QPixmap(track.cover_path)
            if not pix.isNull():
                self._win._ctx.bg_theme.apply(pix)
        else:
            cover = CoverArtService.find_cover(track.uri)
            if cover:
                pix = QPixmap(cover)
                if not pix.isNull():
                    self._win._ctx.bg_theme.apply(pix)
                else:
                    self._win._ctx.bg_theme.reset()
            else:
                self._win._ctx.bg_theme.reset()

        dur = int(track.duration)
        if dur <= 0:
            idx_item = self._win._ctx.items_index.get(track.uri)
            if idx_item:
                dur = int(idx_item.duration)
        if hasattr(self._win, '_mpris_ctrl') and self._win._mpris_ctrl is not None:
            mpris = getattr(self._win._ctx, 'mpris', None)
            if mpris:
                mpris.update_metadata(
                title=name, artist=artist or "",
                album=album, duration=dur)

        self._win._ctx.notify_track(name, artist)
        self._win._ctx.set_window_title(f"Michi Music Player — {name}")

        # Context service
        ctx_svc = getattr(self._win._ctx, "context_svc", None)
        if ctx_svc:
            ctx_svc.update_selection(
                scope="track",
                track=track,
                album=album,
                artist=artist,
                genre=getattr(track, "genre", ""),
                playlist_id=None,
                playlist_name="",
                folder_name="",
                mix_key="",
                search_query="",
            )
            ctx_svc.record_now_playing_updated(name, artist, album)

    def _trackref_from_filepath(self, filepath: str) -> TrackRef:
        item = self._win._ctx.items_index.get(filepath)
        if item:
            return TrackRef(
                uri=item.filepath,
                title=item.title or os.path.basename(item.filepath),
                artist=item.artist,
                album=item.album,
                duration=item.duration,
                year=item.year,
                genre=item.genre,
            )
        return TrackRef(uri=filepath, title=os.path.basename(filepath))

    def play_file(self, filepath: str, add_to_queue: bool = False):
        track = self._trackref_from_filepath(filepath)
        self.play_trackref(track)

    def play_filepaths(self, filepaths: list[str], play_now: bool = True):
        if not filepaths:
            return
        if play_now:
            self.play_file(filepaths[0])
            for fp in filepaths[1:]:
                self._win._ctx.playback.enqueue([fp], play_now=False)
        else:
            self._win._ctx.playback.enqueue(filepaths, play_now=False)

    def on_state(self, state: PlaybackState):
        s = ("playing" if state == PlaybackState.PLAYING else
             "paused" if state == PlaybackState.PAUSED else "stopped")
        self._win._ctx.player_bar.set_state(s)
        if state == PlaybackState.STOPPED:
            self._win._ctx.player_bar.set_position(0)

    def on_stop(self):
        self._win._ctx.playback.stop()
        self._win._ctx.player_bar.reset()
        self._win._ctx.bg_theme.reset()
        self._win._ctx.set_window_title("Michi Music Player")

    def open_eq(self):
        from ui.eq_panel import EqDialog
        dlg = EqDialog(self._win)
        # Load current EQ state from engine
        engine = self._win._ctx.player
        if hasattr(engine, '_engine'):
            eng = engine._engine
            if hasattr(eng, '_eq'):
                eq = eng._eq
                if hasattr(dlg, '_basic'):
                    dlg._basic._bypass_cb.setChecked(eq.mode == "bypass")
                    dlg._basic._preamp_slider.setValue(int(eq.preamp_db * 10))
                    if eq.mode == "graphic" and hasattr(eq, 'bands_31') and eq.bands_31:
                        for i, v in enumerate(eq.bands_31[:31]):
                            if hasattr(dlg._basic, '_sliders') and i < len(dlg._basic._sliders):
                                dlg._basic._sliders[i].setValue(int(v * 10))
        dlg.eq_bands_graphic_changed.connect(
            lambda bands: self._win._ctx.player.set_eq_graphic(bands))
        dlg.eq_bands_parametric_changed.connect(
            lambda bands: self._win._ctx.player.set_eq_parametric(bands))
        dlg.preamp_changed.connect(
            lambda db: self._win._ctx.player.set_eq_preamp(db))
        dlg.eq_bypass_changed.connect(
            lambda bypass: self._win._ctx.player.set_eq_bypass(bypass))
        # Connect spectrum data from engine to spectrum widget
        if hasattr(dlg, '_spectrum'):
            engine = self._win._ctx.player
            if hasattr(engine, 'spectrum_data'):
                engine.spectrum_data.connect(
                    lambda fft: dlg._spectrum.push_fft(fft, 44100))
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self._win._ctx.eq_dlg = dlg

    # ── Context wireup ═══

    def connect_context_events(self, playback=None, context_svc=None):
        playback = playback or getattr(self._win, "_playback", None)
        ctx = context_svc or getattr(self._win, "_context_svc", None)
        if not playback or not ctx:
            return

        from core.context.context_events import AppEvent

        playback.track_changed.connect(
            lambda title, artist: (
                ctx.record_now_playing_updated(title=title, artist=artist),
                ctx.record_track_played_title_artist(title=title, artist=artist),
            )
        )
        playback.state_changed.connect(
            lambda state: ctx.record_track_paused()
            if state == "paused" else None
        )

    # ── Table selection context ═══

    def _resolve_track_model_and_row(self, current):
        """Return (model, row) for a table selection index.

        Resolution order:
        1. current.model() if it has get_trackref()
        2. Proxy model: mapToSource() + sourceModel() with get_trackref()
        3. Registered table model via _track_table_registry
        4. Global window model fallback
        """
        if not current or not current.isValid():
            return None, -1

        model = None
        try:
            model = current.model()
        except Exception:
            model = None

        if model is not None and hasattr(model, "get_trackref"):
            return model, current.row()

        if model is not None:
            try:
                source_model = model.sourceModel() if hasattr(model, "sourceModel") else None
                if source_model is not None and hasattr(source_model, "get_trackref"):
                    source_idx = model.mapToSource(current) if hasattr(model, "mapToSource") else None
                    if source_idx is not None:
                        is_valid = True
                        if hasattr(source_idx, "isValid"):
                            try:
                                is_valid = bool(source_idx.isValid())
                            except Exception:
                                is_valid = False
                        if is_valid and hasattr(source_idx, "row"):
                            return source_model, source_idx.row()
            except Exception:
                pass

        table = getattr(self, "_active_context_table", None)
        if table is not None:
            model = self._ensure_table_model_registry().get(id(table))

        if model is None or not hasattr(model, "get_trackref"):
            model = getattr(self._win._ctx, "model", None)

        if model is not None and hasattr(model, "get_trackref"):
            return model, current.row()

        return None, -1

    def _ensure_table_model_registry(self):
        if not hasattr(self, "_track_table_models"):
            self._track_table_models = {}
        return self._track_table_models

    def attach_track_table(self, table=None, model=None):
        """Attach a track table/model and connect selection context safely.

        Returns the table for chaining.
        """
        table = table or self._win._ctx.table
        if table is None:
            return None

        if model is not None:
            table.setModel(model)
            self._ensure_table_model_registry()[id(table)] = model
        else:
            current_model = table.model() if hasattr(table, "model") else None
            if current_model is not None:
                self._ensure_table_model_registry()[id(table)] = current_model

        self.connect_table_selection(table=table)
        return table

    def detach_track_table(self, table=None):
        """Remove a table from the model registry and clear active table."""
        table = table or getattr(self, "_active_context_table", None)
        if table is None:
            return
        self._ensure_table_model_registry().pop(id(table), None)
        if getattr(self, "_active_context_table", None) is table:
            self._active_context_table = None

    def connect_table_selection(self, table=None):
        """Connect table selection changes to ContextService without playing.

        Only disconnects our slot; never clears unrelated currentChanged listeners.
        Call after each setModel() to keep signal wiring alive.
        """
        table = table or self._win._ctx.table
        if not table:
            return
        self._active_context_table = table
        sel = table.selectionModel()
        if not sel:
            return
        with contextlib.suppress(TypeError, RuntimeError):
            sel.currentChanged.disconnect(self._on_table_selection)
        sel.currentChanged.connect(self._on_table_selection)

    def _on_table_selection(self, current, previous):
        model, row = self._resolve_track_model_and_row(current)
        if model is None or row < 0:
            return

        try:
            track = model.get_trackref(row)
        except (IndexError, KeyError, TypeError, AttributeError):
            return
        except Exception:
            return
        if not track:
            return
        ctx = (
            getattr(getattr(self._win, "_services", None), "context_svc", None)
            or getattr(self._win._ctx, "context_svc", None)
        )
        if ctx:
            ctx.update_selection(
                scope="track",
                track=track,
                album=getattr(track, "album", ""),
                artist=getattr(track, "artist", ""),
                genre=getattr(track, "genre", ""),
                playlist_id=None,
                playlist_name="",
                folder_name="",
                mix_key="",
                search_query="",
            )
