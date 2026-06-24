"""Device sync controller — pairing, manifest generation, persistent storage."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from ui.services.device_registry import DeviceRegistry, PairedDevice
from ui.services.sync_manifest_builder import SyncManifestBuilder, SyncManifest
from ui.services.sync_manifest_store import SyncManifestStore
from ui.services.sync_queue import SyncQueue, SyncJob

logger = logging.getLogger("michi.sync.controller")


class DeviceSyncController(QObject):
    device_paired = Signal(str)
    device_removed = Signal(str)
    manifest_ready = Signal(str, int, int)
    sync_error = Signal(str, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._registry = DeviceRegistry()
        self._manifest_builder = SyncManifestBuilder(db)
        self._manifest_store = SyncManifestStore()
        self._queue = SyncQueue()
        self._manifests: dict[str, SyncManifest] = {}

    @property
    def paired_devices(self) -> list[PairedDevice]:
        return self._registry.list_all()

    def pair_device(self, device_id: str, name: str, host: str = "",
                    port: int = 53318, device_type: str = "android",
                    device_model: str = "", client_version: str = "",
                    capabilities: list | None = None) -> bool:
        ok = self._registry.register(
            device_id, name, host, port, device_type,
            device_model=device_model, client_version=client_version,
        )
        if ok:
            self.device_paired.emit(device_id)
        return ok

    def unpair_device(self, device_id: str):
        self._registry.remove(device_id)
        self._manifests.pop(device_id, None)
        self.device_removed.emit(device_id)

    def build_manifest(self, track_ids: list[int], device_id: str,
                       destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_tracks(
            track_ids, destination_root=destination, device_id=device_id,
        )
        return self._store_manifest(device_id, manifest)

    def build_manifest_from_playlist(self, playlist_id: int, device_id: str,
                                     destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_playlist(
            playlist_id, destination_root=destination, device_id=device_id,
        )
        return self._store_manifest(device_id, manifest)

    def build_manifest_from_favorites(self, device_id: str,
                                      destination: str = "") -> SyncManifest:
        manifest = self._manifest_builder.build_from_favorites(
            destination_root=destination, device_id=device_id,
        )
        return self._store_manifest(device_id, manifest)

    def build_manifest_from_all(self, device_id: str,
                                destination: str = "") -> SyncManifest:
        items = self._db.get_all() if hasattr(self._db, "get_all") else []
        track_ids = [getattr(i, "id", 0) for i in items if getattr(i, "id", 0)]
        return self.build_manifest(track_ids, device_id, destination)

    def _store_manifest(self, device_id: str,
                        manifest: SyncManifest) -> SyncManifest:
        if manifest.total_tracks > 0:
            self._manifests[device_id] = manifest
            public = manifest.to_public_dict()
            self._manifest_store.save(device_id, public)
            self._registry.update(device_id, last_sync=manifest.created_at)
            self.manifest_ready.emit(
                device_id, manifest.total_tracks, manifest.total_size)
        return manifest

    def get_manifest(self, device_id: str) -> SyncManifest | None:
        if device_id in self._manifests:
            return self._manifests[device_id]
        public = self._manifest_store.load_latest(device_id)
        if public:
            manifest = SyncManifest(
                manifest_id=public.get("manifest_id", ""),
                device_id=device_id,
                created_at=public.get("created_at", ""),
                total_tracks=public.get("total_tracks", 0),
                total_size=public.get("total_size", 0),
            )
            self._manifests[device_id] = manifest
            return manifest
        return None

    def get_manifest_public(self, device_id: str) -> dict | None:
        if device_id in self._manifests:
            return self._manifests[device_id].to_public_dict()
        return self._manifest_store.load_latest(device_id)

    def get_manifest_history(self, device_id: str) -> list[dict]:
        return self._manifest_store.load_history(device_id)

    def build_delta_manifest(self, device_id: str, since: float = 0.0) -> dict:
        """Build an incremental delta manifest since a given Unix timestamp."""
        return self._manifest_builder.build_delta(device_id, since)

    def store_delta_manifest(self, device_id: str, delta: dict):
        """Store the latest delta version in manifest store and registry."""
        import time as _time
        ts = _time.strftime("%Y-%m-%dT%H:%M:%S")
        self._manifest_store.save(device_id, delta)
        self._registry.update(device_id, last_sync=ts,
                             last_manifest_ts=str(_time.time()))

    def get_sync_history(self) -> list[SyncJob]:
        return self._queue.get_history()
