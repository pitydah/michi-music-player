"""Playback controller — core track playback, table menus, EQ, state handling."""
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
                self._win._ctx.table.setModel(self._win._ctx.model)
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
            if diag and hasattr(self._win._player_bar, '_quality_badge'):
                self._win._player_bar._quality_badge.set_route_tooltip(diag)
        except Exception:
            pass

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
        if hasattr(self._win, '_mpris_ctrl'):
            self._win._ctx.mpris.update_metadata(
                title=name, artist=artist or "",
                album=album, duration=dur)

        self._win._ctx.notify_track(name, artist)
        self._win._ctx.set_window_title(f"Michi Music Player — {name}")

    def play_file(self, filepath: str, add_to_queue: bool = False):
        track = TrackRef(uri=filepath, title=os.path.basename(filepath))
        self.play_trackref(track)

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
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self._win._ctx.eq_dlg = dlg
