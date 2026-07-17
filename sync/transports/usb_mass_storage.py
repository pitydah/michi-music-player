"""UMS (USB Mass Storage) transport - devices that appear as mounted drives."""
import logging
import os
from pathlib import Path
from ..transport import DeviceTransport, DeviceInfo

logger = logging.getLogger(__name__)

# Common mount points for USB drives
MOUNT_POINTS = ["/media", "/mnt", "/run/media"]


class UsbMassStorageTransport(DeviceTransport):
    """Transport for USB Mass Storage devices (appear as mounted filesystems)."""

    def discover(self) -> list[DeviceInfo]:
        devices = []
        for base in MOUNT_POINTS:
            if not os.path.isdir(base):
                continue
            for entry in os.listdir(base):
                mount_path = Path(base) / entry
                if mount_path.is_mount():
                    # Try to get device info
                    try:
                        stat = os.statvfs(mount_path)
                        total = stat.f_frsize * stat.f_blocks
                        free = stat.f_frsize * stat.f_bfree
                        devices.append(DeviceInfo(
                            device_id=str(mount_path),
                            name=entry,
                            protocols=["ums"],
                            storage_total=total,
                            storage_free=free,
                        ))
                    except OSError:
                        continue
        return devices

    def connect(self, device_id: str) -> bool:
        path = Path(device_id)
        return path.exists() and path.is_mount()

    def disconnect(self, device_id: str) -> bool:
        # UMS devices can't be disconnected via software
        return True

    def list_storage(self, device_id: str) -> list[dict]:
        path = Path(device_id)
        if not path.exists():
            return []
        return [{"id": "root", "path": str(path), "label": path.name}]

    def list_files(self, device_id: str, path: str) -> list[dict]:
        root = Path(device_id)
        target = root / path if not Path(path).is_absolute() else Path(path)
        if not target.exists():
            return []
        files = []
        for f in target.iterdir():
            try:
                files.append({
                    "name": f.name,
                    "path": str(f.relative_to(root)),
                    "size": f.stat().st_size,
                    "is_dir": f.is_dir(),
                })
            except OSError:
                continue
        return files

    def get_device_info(self, device_id: str) -> DeviceInfo:
        path = Path(device_id)
        info = DeviceInfo(device_id=device_id, name=path.name, protocols=["ums"])
        try:
            stat = os.statvfs(path)
            info.storage_total = stat.f_frsize * stat.f_blocks
            info.storage_free = stat.f_frsize * stat.f_bfree
        except OSError:
            pass
        return info
