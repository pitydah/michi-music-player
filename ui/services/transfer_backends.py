"""Transfer backends — Wireless, MTP, and Filesystem for device sync."""

from __future__ import annotations

import logging
import os
import shutil
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("michi.sync.transfer")


@dataclass
class TransferResult:
    track_id: str = ""
    status: str = "pending"
    source_path: str = ""
    dest_path: str = ""
    checksum: str = ""
    error: str = ""
    bytes_transferred: int = 0


class TransferBackend(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def send_file(self, source: str, dest: str, checksum: str = "") -> TransferResult:
        ...


class WirelessSyncBackend(TransferBackend):
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

    def send_file(self, source: str, dest: str, checksum: str = "") -> TransferResult:
        result = TransferResult(source_path=source, dest_path=dest)
        try:
            import urllib.request
            with open(source, "rb") as f:
                data = f.read()
            req = urllib.request.Request(
                f"http://{self._host}:{self._port}/api/stream/{os.path.basename(source)}",
                data=data, method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200:
                    result.status = "completed"
                    result.bytes_transferred = len(data)
                else:
                    result.status = "error"
                    result.error = f"HTTP {r.status}"
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        return result


class MTPBackend(TransferBackend):
    def is_available(self) -> bool:
        import shutil as _shutil
        return _shutil.which("mtpfs") is not None or _shutil.which("jmtpfs") is not None

    def send_file(self, source: str, dest: str, checksum: str = "") -> TransferResult:
        result = TransferResult(source_path=source, dest_path=dest)
        result.status = "not_implemented"
        result.error = "MTP backend pendiente de implementación"
        return result


class FilesystemBackend(TransferBackend):
    def is_available(self) -> bool:
        return True

    def send_file(self, source: str, dest: str, checksum: str = "") -> TransferResult:
        result = TransferResult(source_path=source, dest_path=dest)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            if checksum:
                actual = self._sha256(dest)
                if actual != checksum:
                    result.status = "checksum_mismatch"
                    result.checksum = actual
                    return result
            result.status = "completed"
            result.bytes_transferred = os.path.getsize(dest)
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        return result

    @staticmethod
    def _sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
