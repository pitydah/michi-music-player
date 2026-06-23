"""Transfer backends — Wireless (sync server check), MTP, Filesystem."""

from __future__ import annotations

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
    def is_available(self) -> bool:
        return shutil.which("mtpfs") is not None or shutil.which("jmtpfs") is not None


class FilesystemBackend(TransferBackend):
    def is_available(self) -> bool:
        return True

    def copy_file(self, source: str, dest: str) -> bool:
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            return True
        except Exception as e:
            logger.warning("Filesystem copy failed: %s", e)
            return False
