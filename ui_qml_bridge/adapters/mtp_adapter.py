"""MTPAdapter — MTP device adapter via simple-mtpfs mount."""
from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger("michi.mtp_adapter")

MTP_MOUNT_BASE = "/tmp/michi_mtp"


class MTPAdapter:
    def __init__(self):
        self._mount_point: str | None = None
        self._connected = False

    @property
    def available(self) -> bool:
        try:
            subprocess.run(["simple-mtpfs", "--list-devices"],
                           capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def connect(self, device_id: str = "1") -> dict:
        if self._connected:
            return {"ok": True, "mount_point": self._mount_point}
        mp = os.path.join(MTP_MOUNT_BASE, device_id)
        os.makedirs(mp, exist_ok=True)
        try:
            subprocess.run(["simple-mtpfs", "--device", device_id, mp],
                           check=True, timeout=10)
            self._mount_point = mp
            self._connected = True
            return {"ok": True, "mount_point": mp}
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> dict:
        if not self._connected or not self._mount_point:
            return {"ok": False, "error": "NOT_CONNECTED"}
        try:
            subprocess.run(["fusermount", "-u", self._mount_point],
                           check=True, timeout=10)
            self._connected = False
            self._mount_point = None
            return {"ok": True}
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            return {"ok": False, "error": str(e)}

    def list_storage(self) -> list:
        if not self._connected or not self._mount_point:
            return []
        try:
            return [{"name": d, "path": os.path.join(self._mount_point, d)}
                    for d in os.listdir(self._mount_point)
                    if os.path.isdir(os.path.join(self._mount_point, d))]
        except OSError:
            return []

    def list_files(self, path: str = "") -> list:
        base = path or self._mount_point or ""
        if not base or not os.path.isdir(base):
            return []
        try:
            return [{"name": f, "path": os.path.join(base, f), "size": os.path.getsize(os.path.join(base, f))}
                    for f in os.listdir(base)
                    if os.path.isfile(os.path.join(base, f))]
        except OSError:
            return []

    def transfer(self, src: str, dst: str) -> dict:
        if not os.path.isfile(src):
            return {"ok": False, "error": "SOURCE_NOT_FOUND"}
        try:
            import shutil
            shutil.copy2(src, dst)
            return {"ok": True, "src": src, "dst": dst}
        except Exception as e:
            return {"ok": False, "error": str(e)}
