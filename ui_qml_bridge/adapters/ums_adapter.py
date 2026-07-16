"""UMSAdapter — USB Mass Storage adapter via mount + filesystem."""
from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger("michi.ums_adapter")

UMS_MOUNT_BASE = "/media"
AUDIO_EXTS = frozenset({".flac", ".wav", ".mp3", ".ogg", ".opus",
                         ".m4a", ".wv", ".ape", ".dsf", ".dff", ".aiff"})


class UMSAdapter:
    def __init__(self):
        self._mount_point: str | None = None

    @property
    def available(self) -> bool:
        return True

    def mount(self, device_path: str, mount_point: str = "") -> dict:
        mp = mount_point or os.path.join(UMS_MOUNT_BASE, os.path.basename(device_path))
        os.makedirs(mp, exist_ok=True)
        try:
            subprocess.run(["mount", device_path, mp], check=True, timeout=10)
            self._mount_point = mp
            return {"ok": True, "mount_point": mp}
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            return {"ok": False, "error": str(e)}

    def unmount(self) -> dict:
        if not self._mount_point:
            return {"ok": False, "error": "NOT_MOUNTED"}
        try:
            subprocess.run(["umount", self._mount_point], check=True, timeout=10)
            self._mount_point = None
            return {"ok": True}
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as e:
            return {"ok": False, "error": str(e)}

    def list_files(self, path: str = "") -> list:
        base = path or self._mount_point or ""
        if not base or not os.path.isdir(base):
            return []
        try:
            return [{"name": f, "path": os.path.join(base, f),
                     "size": os.path.getsize(os.path.join(base, f)),
                     "is_audio": os.path.splitext(f)[1].lower() in AUDIO_EXTS}
                    for f in os.listdir(base)
                    if os.path.isfile(os.path.join(base, f))]
        except OSError:
            return []

    def detect_audio(self, path: str = "") -> list:
        all_files = self.list_files(path)
        return [f for f in all_files if f.get("is_audio")]

    def transfer(self, src: str, dst_dir: str) -> dict:
        if not os.path.isfile(src):
            return {"ok": False, "error": "SOURCE_NOT_FOUND"}
        dst = os.path.join(dst_dir, os.path.basename(src))
        try:
            import shutil
            shutil.copy2(src, dst)
            return {"ok": True, "src": src, "dst": dst}
        except Exception as e:
            return {"ok": False, "error": str(e)}
