"""Sync manager — orchestrates HTTP server + UDP discovery + Qt signals.

Single point of control for the wireless music sync feature.
Toggle on/off from the UI, managed here.
"""

import os
from PySide6.QtCore import QObject, Signal

from library.library_db import LibraryDB
from sync.sync_server import SyncServer
from sync.sync_discovery import DiscoveryServer
from sync.local_account import LocalAccountManager


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
        self._server = SyncServer(db, parent=self,
            alias=self._load_alias())
        self._discovery = DiscoveryServer(
            alias=self._load_alias(), parent=self)
        self._active = False
        self._local_account = LocalAccountManager()
        self._device_registry = None

        # Wire security components into the server
        self._server.set_local_account_manager(self._local_account)

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
        self._discovery._auth_required = self._local_account.exists()
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
        self._discovery.alias = alias

    def set_manifest_provider(self, provider):
        """Register a manifest provider for GET /api/sync/manifest."""
        self._server.set_manifest_provider(provider)

    def set_delta_provider(self, provider):
        """Register a delta manifest provider for GET /api/sync/manifest/delta."""
        self._server.set_delta_provider(provider)

    def set_device_registry(self, registry):
        """Register DeviceRegistry for token validation and permission checks."""
        self._device_registry = registry
        self._server.set_device_registry(registry)

    @property
    def local_account(self) -> LocalAccountManager:
        return self._local_account

    def get_peer_info(self, alias: str) -> dict | None:
        """Return stored announce info for a discovered peer."""
        return self._discovery.get_peer_info(alias)

    def get_all_peers(self) -> list[dict]:
        """Return list of all discovered peers with their info."""
        return self._discovery.get_all_peers()

    def _load_alias(self) -> str:
        from core.paths import sync_alias_path
        path = sync_alias_path()
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
        return os.environ.get("USER", "MichiMusicPlayer")

    def _save_alias(self, alias: str):
        from core.paths import app_data_dir, sync_alias_path
        os.makedirs(app_data_dir(), exist_ok=True)
        with open(sync_alias_path(), "w") as f:
            f.write(alias)
