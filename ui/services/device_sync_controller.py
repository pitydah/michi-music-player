"""Device sync controller — orchestrates detection, pairing, manifest, transfer."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from ui.services.device_registry import DeviceRegistry, PairedDevice
from ui.services.sync_manifest_builder import SyncManifestBuilder, SyncManifest
from ui.services.sync_queue import SyncQueue, SyncJob
from ui.services.transcode_service import TranscodeService
from ui.services.transfer_backends import (
    WirelessSyncBackend,
)

logger = logging.getLogger("michi.sync.controller")


class DeviceSyncController(QObject):
    device_detected = Signal(str, str)
    device_paired = Signal(str)
    device_removed = Signal(str)
    sync_started = Signal(str)
    sync_progress = Signal(str, float, int, int)
    sync_completed = Signal(str)
    sync_error = Signal(str, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._registry = DeviceRegistry()
        self._manifest_builder = SyncManifestBuilder(db)
        self._queue = SyncQueue()
        self._transcode = TranscodeService()

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

    def check_device_available(self, host: str, port: int = 53318) -> bool:
        backend = WirelessSyncBackend(host, port)
        return backend.is_available()

    def build_manifest(self, track_ids: list[int], device_id: str,
                       destination: str = "") -> SyncManifest:
        return self._manifest_builder.build_from_tracks(
            track_ids, destination_root=destination, device_id=device_id,
        )

    def build_manifest_from_playlist(self, playlist_id: int, device_id: str,
                                     destination: str = "") -> SyncManifest:
        return self._manifest_builder.build_from_playlist(
            playlist_id, destination_root=destination, device_id=device_id,
        )

    def build_manifest_from_album(self, album: str, artist: str,
                                  device_id: str,
                                  destination: str = "") -> SyncManifest:
        return self._manifest_builder.build_from_album(
            album, artist, destination_root=destination, device_id=device_id,
        )

    def build_manifest_from_favorites(self, device_id: str,
                                      destination: str = "") -> SyncManifest:
        return self._manifest_builder.build_from_favorites(
            destination_root=destination, device_id=device_id,
        )

    def start_sync(self, manifest: SyncManifest, device_id: str):
        device = self._registry.get(device_id)
        if not device:
            self.sync_error.emit("", "Dispositivo no encontrado.")
            return

        job = self._queue.create_job(
            manifest.manifest_id, device_id,
            manifest.total_tracks, manifest.total_size,
        )
        self._queue.start_job(job.job_id)
        self.sync_started.emit(job.job_id)

        self._run_transfer(manifest, device, job)

    def _run_transfer(self, manifest: SyncManifest,
                      device: PairedDevice, job: SyncJob):
        backend = WirelessSyncBackend(device.host, device.port)
        done = 0
        for i, item in enumerate(manifest.items):
            if job.status == "cancelled":
                break
            src = item.get("source_path", "")
            dest = item.get("dest_path", "")
            chk = item.get("checksum", "")
            result = backend.send_file(src, dest, chk)
            if result.status == "completed":
                done += 1
            else:
                self._queue.add_error(job.job_id, f"{item.get('title','')}: {result.error}")
            self._queue.update_progress(job.job_id, i + 1, manifest.total_tracks,
                                        done * item.get("size", 0), manifest.total_size)
            self.sync_progress.emit(job.job_id, job.progress, i + 1, manifest.total_tracks)

        if job.status == "cancelled":
            self._queue.cancel_job(job.job_id)
        else:
            self._queue.complete_job(job.job_id)
            self.sync_completed.emit(job.job_id)

        self._registry.update(device.device_id, last_sync=job.finished_at)

    def cancel_sync(self, job_id: str):
        self._queue.cancel_job(job_id)

    def get_sync_history(self) -> list[SyncJob]:
        return self._queue.get_history()

    def get_transcode_profiles(self) -> dict:
        return dict(self._transcode._profiles)
