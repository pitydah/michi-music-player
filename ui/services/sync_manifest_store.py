"""Sync manifest store — persistent manifest storage on disk."""

from __future__ import annotations

import json
import logging
import os
import time
import contextlib

logger = logging.getLogger("michi.sync.manifest_store")

_BASE_DIR = os.path.expanduser("~/.local/share/michi-music-player/sync_manifests")
_MAX_HISTORY = 20  # keep last N manifests + timestamped files per device


class SyncManifestStore:
    def __init__(self):
        self._base = _BASE_DIR

    def save(self, device_id: str, manifest: dict, public: bool = True):
        device_dir = os.path.join(self._base, device_id)
        os.makedirs(device_dir, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        mid = manifest.get("manifest_id", ts)

        # latest.json (public version)
        latest_path = os.path.join(device_dir, "latest.json")
        data_to_save = manifest.get("tracks", manifest) if public else manifest
        with open(latest_path, "w") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        # timestamped file
        hist_path = os.path.join(device_dir, f"{ts}_{mid}.json")
        with open(hist_path, "w") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        # history index
        history_path = os.path.join(device_dir, "history.json")
        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path) as f:
                    history = json.load(f)
            except Exception:
                pass
        history.append({
            "manifest_id": mid,
            "created_at": manifest.get("created_at", ts),
            "total_tracks": manifest.get("total_tracks", 0),
            "total_size": manifest.get("total_size", 0),
            "file": f"{ts}_{mid}.json",
        })
        with open(history_path, "w") as f:
            json.dump(history[-_MAX_HISTORY:], f, indent=2, ensure_ascii=False)

        # Clean up old timestamped files beyond the limit
        if len(history) > _MAX_HISTORY:
            for entry in history[: -_MAX_HISTORY]:
                fn = entry.get("file", "")
                if fn:
                    with contextlib.suppress(OSError):
                        os.remove(os.path.join(device_dir, fn))

    def load_latest(self, device_id: str) -> dict | None:
        path = os.path.join(self._base, device_id, "latest.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("Manifest load failed: %s", e)
        return None

    def load_history(self, device_id: str) -> list[dict]:
        path = os.path.join(self._base, device_id, "history.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def list_devices(self) -> list[str]:
        if not os.path.exists(self._base):
            return []
        return [d for d in os.listdir(self._base)
                if os.path.isdir(os.path.join(self._base, d))]
