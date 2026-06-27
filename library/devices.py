"""Device detection — mounted filesystems and music scanning."""
import os
import subprocess
import logging

from library.metadata_extractor import ALL_EXTS

logger = logging.getLogger("michi.devices")


def get_mounted_devices() -> list[dict]:
    devices = []
    try:
        r = subprocess.run(["lsblk", "-ln", "-o", "NAME,MOUNTPOINT,FSTYPE,LABEL"],
                          capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) < 2 or not parts[1].startswith("/"):
                continue
            mount = parts[1]
            if mount in ("/", "/boot", "/home", "/etc", "/var", "/usr", "/opt"):
                continue
            if any(mount.startswith(x) for x in ("/sys", "/proc", "/dev", "/run/")):
                continue
            label = parts[3] if len(parts) > 3 else os.path.basename(mount)
            devices.append({"name": label, "mount": mount})
    except Exception as e:
        logger.debug("get_mounted_devices lsblk failed: %s", e)
    for base in ("/run/media/" + os.environ.get("USER", ""), "/media"):
        if os.path.isdir(base):
            for e in os.listdir(base):
                mp = os.path.join(base, e)
                if (os.path.ismount(mp) or os.path.isdir(mp)) and \
                   not any(d["mount"] == mp for d in devices):
                    devices.append({"name": e, "mount": mp})
    return devices


def scan_device_music(mount: str, max_files: int = 0) -> list[str]:
    files = []
    try:
        for root, dirs, fnames in os.walk(mount):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    files.append(os.path.join(root, fn))
            if max_files > 0 and len(files) >= max_files:
                break
    except PermissionError:
        pass
    return files
