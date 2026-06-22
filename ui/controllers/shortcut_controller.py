"""Shortcut controller — manages global keyboard shortcuts."""
from PySide6.QtGui import QShortcut, QKeySequence


class ShortcutController:
    def __init__(self, window, services=None):
        self._win = window
        self._svc = services

    def setup(self):
        QShortcut(QKeySequence("Space"), self._win, self._win._ctx.playback.toggle)
        QShortcut(QKeySequence("Ctrl+Right"), self._win, self._win._ctx.playback.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self._win, self._win._ctx.playback.play_prev)
        QShortcut(QKeySequence("Ctrl+Up"), self._win,
                  lambda: self._win._ctx.player_bar.change_volume(5))
        QShortcut(QKeySequence("Ctrl+Down"), self._win,
                  lambda: self._win._ctx.player_bar.change_volume(-5))
        QShortcut(QKeySequence("Ctrl+M"), self._win,
                  lambda: self._win._ctx.player_bar.mute())
        QShortcut(QKeySequence("Ctrl+F"), self._win,
                  lambda: self._win._search.setFocus())
