"""Shortcut controller — manages global keyboard shortcuts."""
from PySide6.QtGui import QShortcut, QKeySequence


class ShortcutController:
    def __init__(self, window):
        self._win = window

    def setup(self):
        QShortcut(QKeySequence("Space"), self._win, self._win._playback.toggle)
        QShortcut(QKeySequence("Ctrl+Right"), self._win, self._win._playback.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self._win, self._win._playback.play_prev)
        QShortcut(QKeySequence("Ctrl+Up"), self._win,
                  lambda: self._win._player_bar.volume_changed.emit(
                      min(100, self._win._player_bar._vol.value() + 5)))
        QShortcut(QKeySequence("Ctrl+Down"), self._win,
                  lambda: self._win._player_bar.volume_changed.emit(
                      max(0, self._win._player_bar._vol.value() - 5)))
        QShortcut(QKeySequence("Ctrl+M"), self._win,
                  lambda: self._win._player_bar.volume_changed.emit(0))
        QShortcut(QKeySequence("Ctrl+F"), self._win,
                  lambda: self._win._search.setFocus())
