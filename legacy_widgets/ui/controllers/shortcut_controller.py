"""Shortcut controller — manages global keyboard shortcuts."""
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QLineEdit, QTextEdit, QTableView, QAbstractItemView


_EDITABLE_TYPES = (QLineEdit, QTextEdit)


def _focus_is_editable(win) -> bool:
    """Return True if the focused widget is an editable text input or table,
    in which case Alt+Left/Right should not trigger navigation history.
    """
    fw = win.focusWidget()
    if fw is None:
        return False
    if isinstance(fw, _EDITABLE_TYPES):
        return True
    return bool(isinstance(fw, QTableView) and fw.editTriggers() != QAbstractItemView.NoEditTriggers)


class ShortcutController:
    def __init__(self, window, services=None):
        self._win = window
        self._ctx = window._ctx
        self._svc = services

    def setup(self):
        QShortcut(QKeySequence("Space"), self._win, self._ctx.playback.toggle)
        QShortcut(QKeySequence("Ctrl+Right"), self._win, self._ctx.playback.play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self._win, self._ctx.playback.play_prev)
        QShortcut(QKeySequence("Ctrl+Up"), self._win,
                  lambda: self._ctx.player_bar.change_volume(5))
        QShortcut(QKeySequence("Ctrl+Down"), self._win,
                  lambda: self._ctx.player_bar.change_volume(-5))
        QShortcut(QKeySequence("Ctrl+M"), self._win,
                  lambda: self._ctx.player_bar.mute())
        QShortcut(QKeySequence("Ctrl+F"), self._win,
                  lambda: self._ctx.search_widget.setFocus())

        # Navigation history shortcuts (skip if focus is in an editable widget)
        nav_ctrl = getattr(self._win, '_nav_ctrl', None)
        if nav_ctrl:
            QShortcut(QKeySequence("Alt+Left"), self._win,
                      lambda: nav_ctrl.navigate_back() if not _focus_is_editable(self._win) else None)
            QShortcut(QKeySequence("Alt+Right"), self._win,
                      lambda: nav_ctrl.navigate_forward() if not _focus_is_editable(self._win) else None)
