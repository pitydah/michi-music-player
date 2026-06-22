"""MichiApiBridge — thread-safe bridge between HTTP handler and Qt main thread."""
from PySide6.QtCore import QObject, Signal


class MichiApiBridge(QObject):
    """Receives commands from HTTP handler thread, executes on main thread."""

    play_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    volume_requested = Signal(int)
    play_media_requested = Signal(dict)
    select_destination_requested = Signal(str)
    library_play_requested = Signal(dict)
