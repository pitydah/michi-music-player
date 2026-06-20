"""AppContext — dependency container for Astra Music Player controllers."""
from __future__ import annotations


class AppContext:
    """Holds references to the central dependencies of the application.
    Passed to controllers so they don't need direct MainWindow references."""

    def __init__(self, window):
        self.window = window
        self.db = window._db
        self.player = window._player
        self.playback = window._playback
        self.model = window._model
        self.search = window._search_ctrl
