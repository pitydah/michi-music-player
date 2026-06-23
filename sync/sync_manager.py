"""Sync manager — orchestrates HTTP server + UDP discovery + Qt signals.

Single point of control for the wireless music sync feature.
Toggle on/off from the UI, managed here.
"""

import os
from PySide6.QtCore import QObject, Signal

from library.library_db import LibraryDB
from sync.sync_server import SyncServer
from sync.sync_discovery import DiscoveryServer


class SyncManager(QObject):
    """Manages sync server and discovery lifecycle."""

    sync_started = Signal(int)       # port
    sync_stopped = Signal()
    client_connected = Signal(str)   # device alias
    peer_found = Signal(str, str)    # alias, ip
    peer_lost = Signal(str)          # alias
    error_occurred = Signal(str)

    def __init__(self, db: LibraryDB, parent=None):
        super().__init__(parent)
        self._db = db
        self._server = SyncServer(db, parent=self)
        self._discovery = DiscoveryServer(
            alias=self._load_alias(), parent=self)
        self._active = False

        # Wire signals
        self._server.server_started.connect(
            lambda p: self.sync_started.emit(p))
        self._server.server_stopped.connect(
            self.sync_stopped.emit)
        self._server.client_connected.connect(
            self.client_connected.emit)
        self._server.sync_error.connect(
            self.error_occurred.emit)

        self._discovery.peer_found.connect(
            lambda a, ip: self.peer_found.emit(a, ip))
        self._discovery.peer_lost.connect(
            self.peer_lost.emit)
        self._discovery.error_occurred.connect(
            self.error_occurred.emit)

    def start(self):
        if self._active:
            return
        self._active = True
        self._server.start()
        self._discovery.start()

    def stop(self):
        if not self._active:
            return
        self._active = False
        self._server.stop()
        self._discovery.stop()
        self.sync_stopped.emit()

    def toggle(self):
        if self._active:
            self.stop()
        else:
            self.start()

    @property
    def is_active(self) -> bool:
        return self._active

    def set_alias(self, alias: str):
        self._save_alias(alias)
        self._discovery._alias = alias

    def set_manifest_provider(self, provider):
        """Register a manifest provider for GET /api/sync/manifest."""
        self._server.set_manifest_provider(provider)

    def _load_alias(self) -> str:
        path = os.path.expanduser("~/.local/share/michi-music-player/sync_alias")
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
        return os.environ.get("USER", "MichiMusicPlayer")

    def _save_alias(self, alias: str):
        os.makedirs(os.path.expanduser("~/.local/share/michi-music-player"),
                   exist_ok=True)
        with open(os.path.expanduser(
            "~/.local/share/michi-music-player/sync_alias"), "w") as f:
            f.write(alias)
