"""Expanded controller — now playing expanded view management."""
import os

from audio.player import PlaybackState
from library.cover_art_service import CoverArtService
from ui.expanded_view import ExpandedNowPlaying


class ExpandedController:
    def __init__(self, window, services=None):
        self._win = window
        self._svc = services

    def show_expanded(self):
        if not self._win._ctx.playback.current:
            return

        if self._win._ctx.expanded is None:
            self._win._ctx.expanded = ExpandedNowPlaying()
            if hasattr(self._win, '_workers'):
                self._win._ctx.expanded._lyrics._workers = self._win._workers
            self._win._ctx.expanded.go_back.connect(self.back)
            self._win._ctx.expanded.play_clicked.connect(self._win._ctx.playback.toggle)
            self._win._ctx.expanded.prev_clicked.connect(self.prev)
            self._win._ctx.expanded.next_clicked.connect(self.next)
            self._win._ctx.expanded.seek_requested.connect(self._win._ctx.playback.seek)
            self._win._ctx.expanded.volume_changed.connect(self._win._ctx.playback.set_volume)
            self._win._ctx.expanded.track_from_queue.connect(self.queue_track)
            self._win._ctx.expanded.queue_reordered.connect(self._win._ctx.playback.reorder_queue)
            self._win._ctx.expanded.add_to_playlist.connect(
                lambda fp="": self._win._ctx.playlist_ctrl.hub_create_from_folder()
                if hasattr(self._win._ctx, 'playlist_ctrl') else None)
            self._win._ctx.expanded.eq_requested.connect(
                lambda: self._win._show_preferences("eq")
                if hasattr(self._win, '_show_preferences') else None)
            self._win._ctx.expanded.file_info_requested.connect(
                lambda: self._win._open_metadata_for_files(
                    [self._win._ctx.playback.current])
                if self._win._ctx.playback.current and hasattr(self._win, '_open_metadata_for_files') else None)

            self._win._ctx.player.position_changed.connect(self._win._ctx.expanded.set_position)
            self._win._ctx.player.duration_changed.connect(self._win._ctx.expanded.set_duration)
            self._win._ctx.player.state_changed.connect(
                lambda s: self._win._ctx.expanded.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

            self._win._ctx.views.replace("expanded", self._win._ctx.expanded)

        current = self._win._ctx.playback.current
        name = os.path.basename(current) if current else ""
        qual, _ = CoverArtService.quality_label(current) if current else ("", "")
        artist = ""
        album = ""
        dur = 0.0
        cover_path = ""

        if self._win._ctx.current_ref and self._win._ctx.current_ref.uri == current:
            ref = self._win._ctx.current_ref
            name = ref.title or name
            artist = ref.artist
            album = ref.album
            dur = ref.duration
            cover_path = ref.cover_path
            title = ref.title or name
        else:
            title = name
            item = self._win._ctx.items_index.get(current)
            if item:
                artist = item.artist
                album = item.album
                dur = item.duration
                title = item.title or name

        if not cover_path:
            cover = CoverArtService.find_cover(current)
            if cover:
                cover_path = cover

        self._win._ctx.expanded.set_track(title, artist, album, qual, cover_path)
        self._win._ctx.expanded.load_lyrics(title, artist, album, dur)

        self._win._ctx.expanded.set_state(
            "playing" if self._win._ctx.playback.state == PlaybackState.PLAYING else "paused")
        self._win._ctx.expanded.set_queue(self._win._ctx.playback.get_queue())
        self._win._ctx.section_title.setText("Reproduciendo")

        self._win._ctx.views.show("expanded")

    def back(self):
        self._win._ctx.views.show("library")
        self._win._ctx.section_title.setText("Biblioteca")

    def prev(self):
        self._win._ctx.playback.play_prev()
        self.show_expanded()

    def next(self):
        self._win._ctx.playback.play_next()
        self.show_expanded()

    def queue_track(self, filepath: str):
        self._win._ctx.playback.play(filepath)
        self.show_expanded()
