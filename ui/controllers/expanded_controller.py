"""Expanded controller — now playing expanded view management."""
import os

from audio.player import PlaybackState
from library.cover_art_service import CoverArtService
from ui.expanded_view import ExpandedNowPlaying


class ExpandedController:
    def __init__(self, window):
        self._win = window

    def show_expanded(self):
        if not self._win._playback.current:
            return

        if self._win._expanded is None:
            self._win._expanded = ExpandedNowPlaying()
            self._win._expanded.go_back.connect(self.back)
            self._win._expanded.play_clicked.connect(self._win._playback.toggle)
            self._win._expanded.prev_clicked.connect(self.prev)
            self._win._expanded.next_clicked.connect(self.next)
            self._win._expanded.seek_requested.connect(self._win._playback.seek)
            self._win._expanded.volume_changed.connect(self._win._playback.set_volume)
            self._win._expanded.track_from_queue.connect(self.queue_track)
            self._win._expanded.queue_reordered.connect(self._win._playback.reorder_queue)

            self._win._player.position_changed.connect(self._win._expanded.set_position)
            self._win._player.duration_changed.connect(self._win._expanded.set_duration)
            self._win._player.state_changed.connect(
                lambda s: self._win._expanded.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

            self._win._views.replace("expanded", self._win._expanded)

        current = self._win._playback.current
        name = os.path.basename(current) if current else ""
        qual, _ = CoverArtService.quality_label(current) if current else ("", "")
        artist = ""
        album = ""
        dur = 0.0
        cover_path = ""

        if self._win._current_ref and self._win._current_ref.uri == current:
            ref = self._win._current_ref
            name = ref.title or name
            artist = ref.artist
            album = ref.album
            dur = ref.duration
            cover_path = ref.cover_path
            title = ref.title or name
        else:
            title = name
            item = self._win._items_index.get(current)
            if item:
                artist = item.artist
                album = item.album
                dur = item.duration
                title = item.title or name

        if not cover_path:
            cover = CoverArtService.find_cover(current)
            if cover:
                cover_path = cover

        self._win._expanded.set_track(title, artist, album, qual, cover_path)
        self._win._expanded.load_lyrics(title, artist, album, dur)

        self._win._expanded.set_state(
            "playing" if self._win._playback.state == PlaybackState.PLAYING else "paused")
        self._win._expanded.set_queue(self._win._playback.get_queue())
        self._win._section_title.setText("Reproduciendo")

        self._win._views.show("expanded")

    def back(self):
        self._win._views.show("library")
        self._win._section_title.setText("Biblioteca")

    def prev(self):
        self._win._playback.play_prev()
        self.show_expanded()

    def next(self):
        self._win._playback.play_next()
        self.show_expanded()

    def queue_track(self, filepath: str):
        self._win._playback.play(filepath)
        self.show_expanded()
