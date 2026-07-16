"""MiniPlayerController — mini player window lifecycle and signal wiring."""
import os
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.mini_player.controller")


class MiniPlayerController(QObject):
    """Manages the MiniPlayer widget lifecycle, creation, and metadata resolution."""

    mini_player_opened = Signal()
    mini_player_closed = Signal()

    def __init__(self, window, parent=None, services=None):
        super().__init__(parent)
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def open(self):
        """Create or show the mini player window."""
        from ui.mini_player import MiniPlayer
        from audio.player import PlaybackState
        if self._ctx.mini_player is None:
            mp = MiniPlayer(self._ctx.playback, self._win)
            self._ctx.mini_player = mp
            mp.play_clicked.connect(self._ctx.playback.toggle)
            mp.prev_clicked.connect(self._ctx.playback.play_prev)
            mp.next_clicked.connect(self._ctx.playback.play_next)
            mp.seek_requested.connect(self._ctx.playback.seek)
            self._ctx.playback.position_changed.connect(
                lambda s: mp.set_position(
                    s, self._ctx.playback.duration if hasattr(self._ctx.playback, 'duration') else 0))
            self._ctx.playback.state_changed.connect(
                lambda s: mp.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))

        mp = self._ctx.mini_player
        self._update_metadata(mp)
        mp.show()
        mp.raise_()
        mp.activateWindow()
        self.mini_player_opened.emit()

    def close(self):
        """Hide the mini player."""
        if self._ctx.mini_player is not None:
            self._ctx.mini_player.hide()
            self.mini_player_closed.emit()

    def _update_metadata(self, mp):
        current = self._ctx.playback.current
        name = os.path.basename(current) if current else ""
        artist = ""
        if current:
            from library.cover_art_service import CoverArtService
            qual, _ = CoverArtService.quality_label(current)
            item = self._ctx.items_index.get(current)
            if item:
                artist = item.artist or qual or ""
                title = item.title or name
            else:
                title = name
        else:
            title = "Sin reproducción"
        cover_path = CoverArtService.find_cover(current) if current else ""
        mp.set_track(title, artist, cover_path)
