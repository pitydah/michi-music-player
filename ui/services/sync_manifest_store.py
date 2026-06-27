"""Sync manifest store — persistent manifest storage on disk."""

from __future__ import annotations

import logging
import os
import time

from core.json_store import atomic_write_json, read_json_safe
from core.paths import sync_manifest_dir

logger = logging.getLogger("michi.sync.manifest_store")

_BASE_DIR = sync_manifest_dir()


class SyncManifestStore:
    def __init__(self):
        self._base = _BASE_DIR

    def save(self, device_id: str, manifest: dict, public: bool = True):
        device_dir = os.path.join(self._base, device_id)
        os.makedirs(device_dir, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        mid = manifest.get("manifest_id", ts)

        # latest.json — always save full manifest dict
        latest_path = os.path.join(device_dir, "latest.json")
        data_to_save = manifest if (public and isinstance(manifest, dict)) else manifest
        atomic_write_json(latest_path, data_to_save)

        # timestamped file
        hist_path = os.path.join(device_dir, f"{ts}_{mid}.json")
        atomic_write_json(hist_path, data_to_save)

        # history index
        history_path = os.path.join(device_dir, "history.json")
        history = read_json_safe(history_path, default=[], backup_corrupt=True)
        if not isinstance(history, list):
            history = []
        history.append({
            "manifest_id": mid,
            "created_at": manifest.get("created_at", ts),
            "total_tracks": manifest.get("total_tracks", 0),
            "total_size": manifest.get("total_size", 0),
            "file": f"{ts}_{mid}.json",
        })
        atomic_write_json(history_path, history[-20:])

    def load_latest(self, device_id: str) -> dict | None:
        path = os.path.join(self._base, device_id, "latest.json")
        data = read_json_safe(path, default=None, backup_corrupt=True)
        if isinstance(data, list):
            # Legacy: old format stored just the tracks list
            logger.debug("Legacy latest.json (list) detected — wrapping in dict")
            data = {"tracks": data, "manifest_id": "legacy"}
        if isinstance(data, dict):
            return data
        return None

    def load_history(self, device_id: str) -> list[dict]:
        path = os.path.join(self._base, device_id, "history.json")
        data = read_json_safe(path, default=[], backup_corrupt=True)
        if isinstance(data, list):
            return data
        return []

    def list_devices(self) -> list[str]:
        if not os.path.exists(self._base):
            return []
        return [d for d in os.listdir(self._base)
                if os.path.isdir(os.path.join(self._base, d))]
