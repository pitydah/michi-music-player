"""MiniPlayerController — mini player window lifecycle and signal wiring."""
import os
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.mini_player.controller")


class MiniPlayerController(QObject):
    """Manages the MiniPlayer widget lifecycle, creation, and metadata resolution."""

    mini_player_opened = Signal()
    mini_player_closed = Signal()

    def __init__(self, window, parent=None, services=None):
        super().__init__(parent)
        self._win = window
        self._svc = services

    def open(self):
        """Create or show the mini player window."""
        from ui.mini_player import MiniPlayer
        from audio.player import PlaybackState
        if not hasattr(self._win, '_mini_player'):
            self._win._ctx.mini_player = MiniPlayer(
                self._win._ctx.playback, self._win)
            mp = self._win._ctx.mini_player
            mp.play_clicked.connect(self._win._ctx.playback.toggle)
            mp.prev_clicked.connect(self._win._ctx.playback.play_prev)
            mp.next_clicked.connect(self._win._ctx.playback.play_next)
            mp.seek_requested.connect(self._win._ctx.playback.seek)
            self._win._ctx.player.position_changed.connect(
                lambda s: mp.set_position(
                    s, getattr(self._win._ctx.player, '_duration', 0)))
            self._win._ctx.player.state_changed.connect(
                lambda s: mp.set_state(
                    "playing" if s == PlaybackState.PLAYING else
                    "paused" if s == PlaybackState.PAUSED else "stopped"))
            self._win._mini_player = mp

        mp = self._win._ctx.mini_player
        self._update_metadata(mp)
        mp.show()
        mp.raise_()
        mp.activateWindow()
        self.mini_player_opened.emit()

    def close(self):
        """Hide the mini player."""
        if hasattr(self._win, '_mini_player'):
            widget = self._win._ctx.mini_player
            widget.hide()
            self.mini_player_closed.emit()

    def _update_metadata(self, mp):
        current = self._win._ctx.playback.current
        name = os.path.basename(current) if current else ""
        artist = ""
        if current:
            from library.cover_art_service import CoverArtService
            qual, _ = CoverArtService.quality_label(current)
            item = self._win._ctx.items_index.get(current)
            if item:
                artist = item.artist or qual or ""
                title = item.title or name
            else:
                title = name
        else:
            title = "Sin reproducción"
        cover_path = CoverArtService.find_cover(current) if current else ""
        mp.set_track(title, artist, cover_path)
