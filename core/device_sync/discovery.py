"""Device discovery adapters — MSC, MTP and network (Michi Link).

Each adapter returns ``DeviceInfo`` with identity candidates; the serial
is resolved later by the identity priority chain. Protocols are decided
here by the transport (mount source, MTP, Michi Link) — never by
brand-name detection. Brand names found in mount labels are only carried
as vendor hints for the profile resolver.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Protocol

from core.device_sync.models import DeviceInfo, DeviceProtocol

logger = logging.getLogger("michi.device_sync.discovery")

_MSC_ROOTS = ("/media", "/run/media", "/mnt")

# Filesystems that indicate removable storage in /proc/mounts.
_REMOVABLE_FSTYPES = frozenset({
    "vfat", "exfat", "ntfs", "ntfs3", "fuseblk", "ext4", "ext3", "ext2",
    "msdos", "iso9660", "udf",
})


class DeviceDiscoveryAdapter(Protocol):
    """Capability-declared adapter: real probing is adapter-specific."""

    def capability(self) -> str:
        """Declared capability key: msc | mtp | michi_link | network."""
        ...

    def discover(self) -> list[DeviceInfo]:
        """Return detected devices with identity candidates."""
        ...


def _find_audio_dirs(base: str) -> list[str]:
    results = []
    try:
        for entry in os.scandir(base):
            if entry.is_dir(follow_symlinks=False):
                results.append(entry.path)
    except (PermissionError, OSError):
        pass
    return results


def _proc_mounts() -> dict[str, dict]:
    """Parse /proc/mounts → {mountpoint: {device, fstype}}."""
    mounts: dict[str, dict] = {}
    try:
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 3:
                    mounts[parts[1]] = {"device": parts[0], "fstype": parts[2]}
    except OSError:
        pass
    return mounts


def _resolve_device_identity_fields(mount_path: str) -> dict:
    """Resolve fs UUID, volume label and vendor/model from symlinks.

    Pure symlink inspection (``/dev/disk/by-*``) — no subprocess. Returns
    empty fields when nothing resolvable exists (plain test dirs, etc.).
    """
    fields: dict = {"filesystem_uuid": "", "volume_label": "",
                    "vendor": "", "model": "", "usb_serial": ""}
    mounts = _proc_mounts()
    entry = mounts.get(mount_path)
    device_path = entry["device"] if entry else ""

    for link_dir, key in (
        ("/dev/disk/by-uuid", "filesystem_uuid"),
        ("/dev/disk/by-label", "volume_label"),
    ):
        if fields[key]:
            continue
        try:
            for link in Path(link_dir).iterdir():
                try:
                    if os.path.realpath(link) == device_path:
                        fields[key] = link.name
                        break
                except OSError:
                    continue
        except OSError:
            continue

    if device_path:
        # /dev/disk/by-id/usb-Vendor_Model_Serial-0:0 → vendor/model/serial hints
        base = os.path.basename(device_path)
        try:
            by_id = Path("/dev/disk/by-id")
            for link in by_id.iterdir():
                try:
                    if os.path.realpath(link).startswith("/dev/") and (
                        os.path.realpath(link) == device_path
                        or os.path.realpath(link).startswith(
                            os.path.dirname(device_path) + "/" + base
                        )
                    ):
                        name = link.name
                        if name.startswith("usb-"):
                            rest = name[4:].rsplit("-", 1)[0]
                            parts = rest.split("_")
                            if parts:
                                fields["vendor"] = parts[0]
                            if len(parts) > 1:
                                fields["model"] = parts[1]
                            if len(parts) > 2:
                                fields["usb_serial"] = parts[2]
                        break
                except OSError:
                    continue
        except OSError:
            pass
    return fields


class MscDiscoveryAdapter:
    """USB Mass Storage — mount scanning (no external tools)."""

    def __init__(self, roots: tuple = _MSC_ROOTS):
        self._roots = roots

    def capability(self) -> str:
        return "msc"

    def discover(self) -> list[DeviceInfo]:
        results = []
        for root in self._roots:
            try:
                for entry in Path(root).iterdir():
                    if entry.is_dir():
                        info = self.probe(str(entry))
                        if info:
                            results.append(info)
            except (PermissionError, OSError):
                continue
        return results

    def probe(self, mount_path: str) -> DeviceInfo | None:
        try:
            path = Path(mount_path)
            if not path.is_dir():
                return None
            if not _find_audio_dirs(mount_path):
                return None
            fields = _resolve_device_identity_fields(mount_path)
            try:
                usage = os.statvfs(mount_path)
                free = usage.f_frsize * usage.f_bavail
                total = usage.f_frsize * usage.f_blocks
            except OSError:
                free, total = 0, 0
            return DeviceInfo(
                protocol=DeviceProtocol.USB_MASS_STORAGE,
                label=path.name,
                mount_point=mount_path,
                vendor=fields.get("vendor", "") or "",
                model=fields.get("model", "") or "",
                usb_serial=fields.get("usb_serial", "") or "",
                filesystem_uuid=fields.get("filesystem_uuid", "") or "",
                volume_label=fields.get("volume_label", "") or "",
                volume_uuid=fields.get("filesystem_uuid", "") or "",
                music_directory="Music",
                free_bytes=free,
                total_bytes=total,
                capabilities=["msc"],
            )
        except Exception:  # noqa: BLE001
            return None


class MtpDiscoveryAdapter:
    """MTP — capability-declared; probes via ProcessController when wired.

    The probe runs ``simple-mtpfs --list-devices`` through the controlled
    process port when a ProcessController is injected. Without one the
    adapter still declares the MTP capability (planning/transfer can use
    MTP paths) but returns no live devices.
    """

    def __init__(self, process_controller=None, timeout: float = 5.0):
        self._pc = process_controller
        self._timeout = timeout

    def capability(self) -> str:
        return "mtp"

    def discover(self) -> list[DeviceInfo]:
        if self._pc is None:
            return []
        proc = self._pc.spawn_sync(
            "simple-mtpfs", ["--list-devices"], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc is None:
            return []
        deadline = proc.started_at + self._timeout
        while proc.poll() is None and _monotonic() < deadline:
            import time as _time

            _time.sleep(0.05)
        if proc.poll() != 0:
            self._pc.cleanup_sync(proc.pid)
            return []
        lines = []
        if proc._stdout is not None:
            try:
                out = proc._stdout.read().decode("utf-8", errors="replace")
                lines = out.strip().split("\n")
            except (OSError, ValueError):
                pass
        self._pc.cleanup_sync(proc.pid)
        results = []
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            label = line
            results.append(DeviceInfo(
                protocol=DeviceProtocol.ANDROID_MTP,
                label=label,
                mount_point="",
                vendor="Android",
                model=label,
                mtp_id=label.split(":", 1)[0].strip(),
                music_directory="Music",
                capabilities=["mtp"],
            ))
        return results


def _monotonic() -> float:
    import time

    return time.monotonic()


class NetworkDiscoveryAdapter:
    """Michi Link / network filesystems — capability-declared.

    Live peer discovery belongs to the Michi Link client / Connection
    service; this adapter only declares the capability so planning and
    profiles can handle network devices without fabricating devices.
    """

    def capability(self) -> str:
        return "michi_link"

    def discover(self) -> list[DeviceInfo]:
        return []


class DiscoveryComposite:
    """Run every injected adapter; results are identities, not facts."""

    def __init__(self, adapters: list):
        self._adapters = list(adapters)

    @property
    def adapters(self) -> list:
        return list(self._adapters)

    def discover(self) -> list[DeviceInfo]:
        results = []
        for adapter in self._adapters:
            try:
                results.extend(adapter.discover() or [])
            except Exception:  # noqa: BLE001
                logger.debug("Discovery adapter %s failed", adapter, exc_info=True)
        return results

    def probe(self, mount_path: str) -> DeviceInfo | None:
        for adapter in self._adapters:
            if not hasattr(adapter, "probe"):
                continue
            try:
                info = adapter.probe(mount_path)
            except Exception:  # noqa: BLE001
                continue
            if info is not None:
                return info
        return None
