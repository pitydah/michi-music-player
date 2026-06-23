"""Device sync controller — pairing, manifest generation, sync status."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from ui.services.device_registry import DeviceRegistry, PairedDevice
from ui.services.sync_manifest_builder import SyncManifestBuilder, SyncManifest
from ui.services.sync_queue import SyncQueue, SyncJob

logger = logging.getLogger("michi.sync.controller")


class DeviceSyncController(QObject):
    device_paired = Signal(str)
    device_removed = Signal(str)
    manifest_ready = Signal(str, int)
    sync_error = Signal(str, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._registry = DeviceRegistry()
        self._manifest_builder = SyncManifestBuilder(db)
        self._queue = SyncQueue()

    @property
    def paired_devices(self) -> list[PairedDevice]:
        return self._registry.list_all()

    def pair_device(self, device_id: str, name: str, host: str = "",
                    port: int = 53318, device_type: str = "android") -> bool:
        ok = self._registry.register(device_id, name, host, port, device_type)
        if ok:
            self.device_paired.emit(device_id)
        return ok

    def unpair_device(self, device_id: str):
        self._registry.remove(device_id)
        self.device_removed.emit(device_id)

    def build_manifest(self, track_ids: list[int], device_id: str,
                       destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_tracks(
            track_ids, destination_root=destination, device_id=device_id,
        )
        if manifest.total_tracks > 0:
            self.manifest_ready.emit(device_id, manifest.total_tracks)
        return manifest

    def build_manifest_from_playlist(self, playlist_id: int, device_id: str,
                                     destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_playlist(
            playlist_id, destination_root=destination, device_id=device_id,
        )
        if manifest.total_tracks > 0:
            self.manifest_ready.emit(device_id, manifest.total_tracks)
        return manifest

    def build_manifest_from_favorites(self, device_id: str,
                                      destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_favorites(
            destination_root=destination, device_id=device_id,
        )
        if manifest.total_tracks > 0:
            self.manifest_ready.emit(device_id, manifest.total_tracks)
        return manifest

    def get_sync_history(self) -> list[SyncJob]:
        return self._queue.get_history()
