"""Playback controller — core business logic, no UI framework dependency."""
from __future__ import annotations

import contextlib
import logging
import os
from typing import Any

from PySide6.QtCore import QModelIndex, QPoint, Qt
from PySide6.QtGui import QPixmap

from audio.player import PlaybackState
from audio.quality_classifier import classify_audio_quality
from sources.base_source import TrackRef
from library.trackref_model import TrackRefTableModel
from library.cover_art_service import CoverArtService


logger = logging.getLogger("michi.playback")


class PlaybackController:
    """Coordinate playback requests and their UI/context presentation."""

    def __init__(self, window: Any, queue_service: Any | None = None,
                 player_service: Any | None = None) -> None:
        self._win = window
        self._queue = queue_service
        self._player = player_service

    def _require_queue(self) -> Any:
        if self._queue is None:
            raise RuntimeError("PlaybackController requires QueueService for queue operations")
        return self._queue

    def _require_player(self) -> Any:
        if self._player is None:
            raise RuntimeError("PlaybackController requires PlayerService for transport")
        return self._player

    def on_table_menu(self, pos: QPoint) -> None:
        pass

    def _add_to_new_playlist(self, filepath: str) -> None:
        pass

    def edit_tags(self, filepath: str) -> None:
        pass

    def on_table_dbl(self, idx: QModelIndex) -> None:
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

    def play_trackref(self, track: TrackRef) -> None:
        self._start_track_playback(track)
        self._present_track(track)

    def _start_track_playback(self, track: TrackRef) -> None:
        self._win._ctx.current_ref = track

        if track.uri.startswith("http"):
            self._require_player().play_url(track.uri, track.title, track.artist)
        else:
            self._require_queue().enqueue([track.uri], play_now=True)

    def _present_track(self, track: TrackRef) -> None:
        name, artist, album, quality_str, item = self._track_presentation_data(track)
        self._update_player_bar(track, item, quality_str)
        self._update_route_diagnostics()
        self._update_background(track)
        self._update_mpris_metadata(track, name, artist, album)
        self._show_track_notification(name, artist)
        self._update_playback_context(track, name, artist, album)

    def _track_presentation_data(self, track: TrackRef) -> tuple[str, str, str, str, Any | None]:
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

        return name, artist, album, quality_str, item

    def _update_player_bar(self, track: TrackRef, item: Any | None, quality_str: str) -> None:
        self._win._ctx.player_bar.set_track_from_ref(track)
        self._win._ctx.player_bar.set_quality(quality_str)

        qc = classify_audio_quality(item) if item else {"category": "unknown", "label": quality_str, "tooltip": ""}
        self._win._ctx.player_bar.set_quality_info(
            qc.get("label", quality_str),
            qc.get("category", "unknown"),
            qc.get("tooltip", ""))

    def _update_route_diagnostics(self) -> None:
        try:
            diag = self._win._ctx.player.get_audio_diagnostics() if hasattr(
                self._win._ctx.player, 'get_audio_diagnostics') else None
            if diag and hasattr(self._win, '_player_bar_ctrl') and self._win._player_bar_ctrl:
                self._win._player_bar_ctrl.set_route_tooltip(diag)
        except Exception:
            logger.debug("audio diagnostics not available")

    def _update_background(self, track: TrackRef) -> None:
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

    def _update_mpris_metadata(
        self,
        track: TrackRef,
        name: str,
        artist: str,
        album: str,
    ) -> None:
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

    def _show_track_notification(self, name: str, artist: str) -> None:
        self._win._ctx.notify_track(name, artist)
        self._win._ctx.set_window_title(f"Michi Music Player — {name}")

    def _update_playback_context(
        self,
        track: TrackRef,
        name: str,
        artist: str,
        album: str,
    ) -> None:
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

    def play_file(self, filepath: str, add_to_queue: bool = False) -> None:
        track = self._trackref_from_filepath(filepath)
        self.play_trackref(track)

    def play_filepaths(self, filepaths: list[str], play_now: bool = True) -> None:
        if not filepaths:
            return
        if play_now:
            self.play_file(filepaths[0])
            for fp in filepaths[1:]:
                self._require_queue().enqueue([fp], play_now=False)
        else:
            self._require_queue().enqueue(filepaths, play_now=False)

    def on_state(self, state: PlaybackState) -> None:
        s = ("playing" if state == PlaybackState.PLAYING else
             "paused" if state == PlaybackState.PAUSED else "stopped")
        self._win._ctx.player_bar.set_state(s)
        if state == PlaybackState.STOPPED:
            self._win._ctx.player_bar.set_position(0)

    def on_stop(self) -> None:
        self._require_player().stop()
        self._win._ctx.player_bar.reset()
        self._win._ctx.bg_theme.reset()
        self._win._ctx.set_window_title("Michi Music Player")

    def open_eq(self) -> None:
        pass

    def connect_context_events(
        self,
        playback: Any | None = None,
        context_svc: Any | None = None,
    ) -> None:
        playback = playback or getattr(self._win, "_playback", None)
        ctx = context_svc or getattr(self._win, "_context_svc", None)
        if not playback or not ctx:
            return
        if getattr(self, "_context_events_connected", False):
            return
        self._context_events_connected = True
        self._context_queue_was_active = False
        self._context_svc_for_events = ctx
        self._last_context_track_key = None
        playback.track_changed.connect(self._on_track_changed_for_context)
        playback.state_changed.connect(
            lambda state: ctx.record_track_paused()
            if state == "paused" else None
        )
        playback.queue_changed.connect(self._on_queue_changed_for_context)

    def _on_track_changed_for_context(self, title: str, artist: str) -> None:
        ctx = getattr(self, "_context_svc_for_events", None)
        if not ctx:
            return
        key = ((title or "").strip(), (artist or "").strip())
        if key == getattr(self, "_last_context_track_key", None):
            ctx.record_now_playing_updated(title=title, artist=artist)
            return
        self._last_context_track_key = key
        ctx.record_now_playing_updated(title=title, artist=artist)
        ctx.record_track_played_title_artist(title=title, artist=artist)

    def _on_queue_changed_for_context(self, queue: Any) -> None:
        ctx = getattr(self, "_context_svc_for_events", None)
        if not ctx:
            return
        count = len(queue or [])
        was_active = getattr(self, "_context_queue_was_active", False)
        if count <= 0:
            if was_active:
                ctx.record_queue_cleared(reason="queue_empty")
            self._context_queue_was_active = False
            return
        self._context_queue_was_active = True
        ctx.record_queue_updated(count=count, source="playback")

    def _context(self) -> Any | None:
        return (
            getattr(getattr(self._win, "_services", None), "context_svc", None)
            or getattr(self._win._ctx, "context_svc", None)
        )

    @staticmethod
    def _read_attr(playback: Any, *attrs: str) -> Any | None:
        for attr in attrs:
            if hasattr(playback, attr):
                value = getattr(playback, attr)
                return value() if callable(value) else value
        return None

    def _read_shuffle_state(self) -> Any | None:
        return self._read_attr(self._require_queue(), "shuffle", "shuffle_enabled", "_shuffle")

    def _read_repeat_state(self) -> Any | None:
        return self._read_attr(self._require_queue(), "repeat", "repeat_mode", "_repeat")

    def toggle_shuffle_with_context(self) -> None:
        self._require_queue().toggle_shuffle()
        ctx = self._context()
        if ctx:
            ctx.record_playback_mode_changed(shuffle=self._read_shuffle_state())

    def toggle_repeat_with_context(self) -> None:
        result = self._require_queue().toggle_repeat()
        new_mode = result.get("mode") if isinstance(result, dict) else None
        ctx = self._context()
        if ctx:
            ctx.record_playback_mode_changed(repeat=new_mode or self._read_repeat_state())

    def enqueue_with_context(
        self,
        filepaths: list[str],
        play_now: bool = True,
        source: str = "library",
        title: str = "",
        artist: str = "",
    ) -> None:
        ctx = self._context()
        queue = self._require_queue()
        if not ctx or not filepaths:
            queue.enqueue(filepaths, play_now=play_now)
            return
        if len(filepaths) == 1 and (title or artist):
            ctx.record_track_queued(title=title, artist=artist, source=source)
        else:
            ctx.record_track_queued(source=source)
        queue.enqueue(filepaths, play_now=play_now)
        final_count = self._read_attr(queue, "count")
        payload_count = final_count if final_count is not None else len(filepaths)
        ctx.record_queue_updated(count=payload_count, source=source, added_count=len(filepaths))

    def _resolve_track_model_and_row(self, current: QModelIndex) -> tuple[Any | None, int]:
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

    def _ensure_table_model_registry(self) -> dict[int, Any]:
        if not hasattr(self, "_track_table_models"):
            self._track_table_models = {}
        return self._track_table_models

    def attach_track_table(
        self,
        table: Any | None = None,
        model: Any | None = None,
    ) -> Any | None:
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

    def detach_track_table(self, table: Any | None = None) -> None:
        table = table or getattr(self, "_active_context_table", None)
        if table is None:
            return
        self._ensure_table_model_registry().pop(id(table), None)
        if getattr(self, "_active_context_table", None) is table:
            self._active_context_table = None

    def connect_table_selection(self, table: Any | None = None) -> None:
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

    def _on_table_selection(self, current: QModelIndex, previous: QModelIndex) -> None:
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
