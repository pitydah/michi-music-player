"""Transfer backends — Wireless (sync server check), MTP, Filesystem."""

from __future__ import annotations

import json
import logging
import os
import shutil
from abc import ABC, abstractmethod

logger = logging.getLogger("michi.sync.transfer")


class TransferBackend(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        ...


class WirelessSyncBackend(TransferBackend):
    """Check if a Michi Sync server (KDE or Android) is reachable.
    KDE serves the library. Android downloads using the manifest."""
    def __init__(self, host: str = "", port: int = 53318):
        self._host = host
        self._port = port

    def is_available(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://{self._host}:{self._port}/api/ping", method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False


class MTPBackend(TransferBackend):
    """MTP device transfer — requires jmtpfs or mtpfs mount helper."""
    def is_available(self) -> bool:
        return shutil.which("mtpfs") is not None or shutil.which("jmtpfs") is not None

    def mount_path(self) -> str | None:
        """Return common MTP mount points if available."""
        for mp in ("/run/user/1000/gvfs", "/media", "/mnt"):
            if os.path.isdir(mp):
                return mp
        return None


class UsbSyncPackageBuilder:
    """Build a USB copy tree from a SyncManifest for filesystem-based sync.

    Output structure:
        /MichiSync/
            manifest.json
            playlists.json
            tracks/
            covers/
            checksums.json
    """
    def __init__(self, manifest: dict, dest_root: str):
        self._manifest = manifest
        self._dest_root = dest_root

    def build_structure(self) -> bool:
        try:
            sync_dir = os.path.join(self._dest_root, "MichiSync")
            os.makedirs(os.path.join(sync_dir, "tracks"), exist_ok=True)
            os.makedirs(os.path.join(sync_dir, "covers"), exist_ok=True)

            with open(os.path.join(sync_dir, "manifest.json"), "w") as f:
                json.dump(self._manifest, f, indent=2)

            if self._manifest.get("playlists"):
                with open(os.path.join(sync_dir, "playlists.json"), "w") as f:
                    json.dump(self._manifest["playlists"], f, indent=2)

            return True
        except Exception as e:
            logger.warning("UsbSyncPackageBuilder failed: %s", e)
            return False


class FilesystemBackend(TransferBackend):
    def __init__(self, base_path: str = ""):
        self._base = base_path

    def is_available(self) -> bool:
        return bool(self._base) if self._base else True

    def copy_file(self, source: str, dest: str) -> bool:
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            return True
        except Exception as e:
            logger.warning("Filesystem copy failed: %s", e)
            return False

    def copy_manifest_to(self, manifest: dict, dest_root: str) -> bool:
        builder = UsbSyncPackageBuilder(manifest, dest_root)
        return builder.build_structure()
