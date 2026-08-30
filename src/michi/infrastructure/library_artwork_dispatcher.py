"""Qt owner-thread adapter for LibraryArtworkRefresh (R4 ABSOLUTE FINAL).

LibraryArtworkRefresh is Application logic — Qt lives HERE, at the explicit
infrastructure thread boundary. The relay's queued completion routes
through this dispatcher so owner-side publication runs on the Qt owner
thread, and shutdown() severs the reference before the lifecycle is torn
down (a late relay event can never call a destroyed object).
"""

from PySide6.QtCore import QObject, Slot


class LibraryArtworkDispatcher(QObject):
    """Qt owner-thread adapter for LibraryArtworkRefresh."""

    def __init__(self, refresh, parent=None):
        super().__init__(parent)
        self._refresh = refresh

    @Slot(int, object, object)
    def on_done(self, generation: int, result, error) -> None:
        refresh = self._refresh
        if refresh is None:
            return
        refresh.handle_done(generation, result, error)

    def shutdown(self) -> None:
        self._refresh = None
