"""Expanded controller — now playing expanded view management."""
import os

from PySide6.QtCore import QObject, Signal
from audio.player import PlaybackState
from library.cover_art_service import CoverArtService
from ui.expanded_view import ExpandedNowPlaying


class ExpandedController(QObject):
    play_files_requested = Signal(list)
    metadata_requested = Signal(list)
    preferences_requested = Signal(str)

    def __init__(self, window, services=None):
        super().__init__()
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def show_expanded(self):
        if not self._ctx.playback.current:
            return

        if self._ctx.expanded is None:
            self._ctx.expanded = ExpandedNowPlaying()
            if self._svc and hasattr(self._svc, 'workers') and self._svc.workers:
                self._ctx.expanded.set_worker_manager(self._svc.workers)
            else:
                self._ctx.expanded.set_worker_manager(self._ctx.workers)
            self._ctx.expanded.go_back.connect(self.back)
            self._ctx.expanded.play_clicked.connect(self._ctx.playback.toggle)
            self._ctx.expanded.prev_clicked.connect(self.prev)
            self._ctx.expanded.next_clicked.connect(self.next)
            self._ctx.expanded.seek_requested.connect(self._ctx.playback.seek)
            self._ctx.expanded.volume_changed.connect(self._ctx.playback.set_volume)
            self._ctx.expanded.track_from_queue.connect(self.queue_track)
            self._ctx.expanded.queue_reordered.connect(self._ctx.playback.reorder_queue)
            self._ctx.expanded.add_to_playlist.connect(
                lambda fp="": self._ctx.playlist_ctrl.hub_create_from_folder()
                if hasattr(self._ctx, 'playlist_ctrl') else None)
            self._ctx.expanded.eq_requested.connect(
                lambda: self.preferences_requested.emit("eq"))
            self._ctx.expanded.file_info_requested.connect(
                lambda: self.metadata_requested.emit(
                    [self._ctx.playback.current])
                if self._ctx.playback.current else None)

            self._ctx.playback.position_changed.connect(self._ctx.expanded.set_position)
            self._ctx.playback.duration_changed.connect(self._ctx.expanded.set_duration)
            self._ctx.playback.state_changed.connect(
                lambda s: self._ctx.expanded.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

            self._ctx.views.replace("expanded", self._ctx.expanded)

        current = self._ctx.playback.current
        name = os.path.basename(current) if current else ""
        qual, _ = CoverArtService.quality_label(current) if current else ("", "")
        artist = ""
        album = ""
        dur = 0.0
        cover_path = ""

        if self._ctx.current_ref and self._ctx.current_ref.uri == current:
            ref = self._ctx.current_ref
            name = ref.title or name
            artist = ref.artist
            album = ref.album
            dur = ref.duration
            cover_path = ref.cover_path
            title = ref.title or name
        else:
            title = name
            item = self._ctx.items_index.get(current)
            if item:
                artist = item.artist
                album = item.album
                dur = item.duration
                title = item.title or name

        if not cover_path:
            cover = CoverArtService.find_cover(current)
            if cover:
                cover_path = cover

        self._ctx.expanded.set_track(title, artist, album, qual, cover_path)
        self._ctx.expanded.load_lyrics(title, artist, album, dur)

        self._ctx.expanded.set_state(
            "playing" if self._ctx.playback.state == PlaybackState.PLAYING else "paused")
        self._ctx.expanded.set_queue(self._ctx.playback.get_queue())
        self._ctx.section_title.setText("Reproduciendo")

        self._ctx.views.show("expanded")

    def back(self):
        self._ctx.views.show("library")
        self._ctx.section_title.setText("Biblioteca")

    def prev(self):
        self._ctx.playback.play_prev()
        self.show_expanded()

    def next(self):
        self._ctx.playback.play_next()
        self.show_expanded()

    def queue_track(self, filepath: str):
        self._ctx.playback.play(filepath)
        self.show_expanded()
