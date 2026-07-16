"""DeviceSyncService — audio-only device sync for Android (MTP), USB Mass Storage,
and generic dedicated players (HiBy, FiiO, Ruizu, etc.).

Brands are resolved by capabilities/protocols, not by brand-specific code.
Supported capabilities: discovery, device identity, storage, formats, music directory,
pairing, authorization, unpair, trust, transfer job, progress, cancel, retry,
history, errors, playlist compatibility. Audio only.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("michi.device_sync")

AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".wv", ".ogg", ".opus", ".m4a", ".aac",
    ".wma", ".dsf", ".dff", ".ape", ".aiff", ".aif", ".mpc",
})

TRANSFER_CHUNK_SIZE = 65536

AUDIO_PLAYLIST_EXTENSIONS = frozenset({".m3u", ".m3u8", ".pls", ".xspf"})


class DeviceProtocol(Enum):
    ANDROID_MTP = "android_mtp"
    USB_MASS_STORAGE = "usb_mass_storage"
    GENERIC_DEDICATED = "generic_dedicated"
    UNKNOWN = "unknown"


class SyncDirection(Enum):
    TO_DEVICE = "to_device"
    FROM_DEVICE = "from_device"


class TransferStatus(Enum):
    QUEUED = "queued"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class DeviceIdentity:
    protocol: DeviceProtocol = DeviceProtocol.UNKNOWN
    vendor: str = ""
    model: str = ""
    serial: str = ""
    label: str = ""
    mount_point: str = ""
    usb_vendor_id: str = ""
    usb_product_id: str = ""


@dataclass
class DeviceCapabilities:
    supports_pairing: bool = False
    supports_authorization: bool = False
    supports_trust: bool = False
    supports_progress: bool = True
    supports_cancel: bool = True
    supports_retry: bool = True
    supports_playlists: bool = False
    max_filename_length: int = 255
    max_path_length: int = 4096
    supported_formats: set = field(default_factory=lambda: set(AUDIO_EXTENSIONS))
    music_directory: str = "Music"


@dataclass
class StorageInfo:
    total_bytes: int = 0
    free_bytes: int = 0
    used_bytes: int = 0
    label: str = "Internal storage"
    is_removable: bool = False


@dataclass
class TransferJob:
    job_id: str
    source_path: str
    dest_path: str
    direction: SyncDirection = SyncDirection.TO_DEVICE
    status: TransferStatus = TransferStatus.QUEUED
    total_bytes: int = 0
    transferred_bytes: int = 0
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    cancelled: bool = False


@dataclass
class SyncHistoryEntry:
    job_id: str
    device_label: str
    timestamp: float
    direction: SyncDirection
    status: TransferStatus
    total_bytes: int
    transferred_bytes: int
    error: str


@dataclass
class PairedDevice:
    identity: DeviceIdentity
    capabilities: DeviceCapabilities
    authorized: bool = False
    trusted: bool = False
    paired_at: float = 0.0
    last_contact: float = 0.0


def _format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1048576:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1073741824:
        return f"{bytes_val / 1048576:.1f} MB"
    return f"{bytes_val / 1073741824:.2f} GB"


def _safe_filename(name: str, max_len: int = 255) -> str:
    safe = "".join(c if c.isalnum() or c in " ._-()[]" else "_" for c in name)
    if len(safe) > max_len:
        base, ext = os.path.splitext(safe)
        safe = base[:max_len - len(ext)] + ext
    return safe


def _is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def _is_playlist_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_PLAYLIST_EXTENSIONS


class DeviceSyncService:
    def __init__(self):
        self._lock = threading.Lock()
        self._paired: dict[str, PairedDevice] = {}
        self._discovered: dict[str, DeviceIdentity] = {}
        self._jobs: dict[str, TransferJob] = {}
        self._history: list[SyncHistoryEntry] = []
        self._max_history = 100
        self._callbacks: dict[str, list[Callable]] = {}
        self._job_counter = 0
        self._on_progress: Callable[[TransferJob], None] | None = None

    # ── Event callbacks ──

    def set_on_progress(self, cb: Callable[[TransferJob], None] | None):
        self._on_progress = cb

    def _notify(self, event: str, data: Any = None):
        with self._lock:
            cbs = list(self._callbacks.get(event, []))
        for cb in cbs:
            try:
                cb(data)
            except Exception:
                logger.debug("Callback %s failed", event, exc_info=True)

    def on(self, event: str, cb: Callable):
        with self._lock:
            self._callbacks.setdefault(event, []).append(cb)

    def off(self, event: str, cb: Callable):
        with self._lock:
            try:
                self._callbacks[event].remove(cb)
            except (ValueError, KeyError):
                return

    # ── Discovery ──

    def discover(self) -> list[DeviceIdentity]:
        results: list[DeviceIdentity] = []
        self._discovered.clear()
        try:
            for entry in Path("/media").iterdir():
                if entry.is_dir():
                    dev = self._probe_mount(str(entry))
                    if dev:
                        results.append(dev)
        except (PermissionError, OSError):
            pass
        try:
            for entry in Path("/run/media").iterdir():
                if entry.is_dir() and entry.name not in self._discovered:
                    dev = self._probe_mount(str(entry))
                    if dev:
                        results.append(dev)
        except (PermissionError, OSError):
            pass
        self._check_mtp_devices(results)
        for dev in results:
            key = f"{dev.protocol.value}:{dev.serial or dev.mount_point}"
            self._discovered[key] = dev
        return results

    def _probe_mount(self, mount_path: str) -> DeviceIdentity | None:
        try:
            path = Path(mount_path)
            if not path.is_dir():
                return None
            audio_dirs = self._find_audio_dirs(mount_path)
            if not audio_dirs:
                return None
            label = path.name
            serial = str(hash(mount_path))[-8:]
            vendor, model = self._detect_device_via_path(mount_path)
            proto = DeviceProtocol.USB_MASS_STORAGE
            if "android" in label.lower():
                proto = DeviceProtocol.ANDROID_MTP
            if vendor.lower() in ("hiby", "fiio", "ruizu", "sony", "sandisk", "creative"):
                proto = DeviceProtocol.GENERIC_DEDICATED
            return DeviceIdentity(
                protocol=proto, vendor=vendor, model=model,
                serial=serial, label=label, mount_point=mount_path,
            )
        except Exception:
            return None

    def _detect_device_via_path(self, mount_path: str) -> tuple[str, str]:
        label = Path(mount_path).name.lower()
        known_vendors = {
            "hiby", "fiio", "ruizu", "sony", "sandisk", "creative",
            "apple", "google", "samsung", "xiaomi", "oneplus",
        }
        for v in known_vendors:
            if v in label:
                return (v.capitalize(), label)
        return ("Unknown", label)

    def _find_audio_dirs(self, base: str) -> list[str]:
        results = []
        try:
            for entry in os.scandir(base):
                if entry.is_dir(follow_symlinks=False):
                    results.append(entry.path)
        except PermissionError:
            pass
        return results

    def _check_mtp_devices(self, results: list[DeviceIdentity]):
        try:
            import subprocess
            out = subprocess.run(["simple-mtpfs", "--list-devices"],
                                 capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                for line in out.stdout.strip().split("\n"):
                    if ":" in line:
                        label = line.strip()
                        results.append(DeviceIdentity(
                            protocol=DeviceProtocol.ANDROID_MTP,
                            vendor="Android",
                            model=label,
                            serial=str(hash(label))[-8:],
                            label=label,
                            mount_point="",
                        ))
        except Exception:
            pass

    def get_discovered(self) -> list[DeviceIdentity]:
        return list(self._discovered.values())

    # ── Device identity ──

    def identify(self, mount_point: str) -> DeviceIdentity | None:
        for dev in self._discovered.values():
            if dev.mount_point == mount_point:
                return dev
        for dev in self._paired.values():
            if dev.identity.mount_point == mount_point:
                return dev.identity
        return self._probe_mount(mount_point)

    def resolve_capabilities(self, identity: DeviceIdentity) -> DeviceCapabilities:
        proto = identity.protocol
        if proto == DeviceProtocol.ANDROID_MTP:
            return DeviceCapabilities(
                supports_pairing=True, supports_authorization=True,
                supports_trust=True, supports_playlists=True,
                music_directory="Music",
            )
        if proto == DeviceProtocol.USB_MASS_STORAGE:
            vendor_lower = identity.vendor.lower()
            if "hiby" in vendor_lower or "fiio" in vendor_lower or "sony" in vendor_lower:
                return DeviceCapabilities(
                    supports_pairing="hiby" in vendor_lower,
                    supports_authorization=False, supports_trust=True,
                    supports_playlists=True, music_directory="Music",
                )
            if "ruizu" in vendor_lower:
                return DeviceCapabilities(
                    supports_pairing=False, supports_authorization=False,
                    supports_trust=False, supports_playlists=True,
                    music_directory="Music",
                )
            return DeviceCapabilities(
                supports_pairing=False, supports_authorization=False,
                supports_trust=False, supports_playlists=False,
                music_directory="Music",
            )
        if proto == DeviceProtocol.GENERIC_DEDICATED:
            vendor_lower = identity.vendor.lower()
            if "hiby" in vendor_lower or "fiio" in vendor_lower or "sony" in vendor_lower:
                return DeviceCapabilities(
                    supports_pairing="hiby" in vendor_lower,
                    supports_authorization=False, supports_trust=True,
                    supports_playlists=True, music_directory="Music",
                )
            return DeviceCapabilities(
                supports_pairing=False, supports_authorization=False,
                supports_trust=False, supports_playlists=False,
                music_directory="Music",
            )
        return DeviceCapabilities()

    def get_storage(self, mount_point: str) -> StorageInfo:
        try:
            st = os.statvfs(mount_point)
            return StorageInfo(
                total_bytes=st.f_frsize * st.f_blocks,
                free_bytes=st.f_frsize * st.f_bfree,
                used_bytes=st.f_frsize * (st.f_blocks - st.f_bfree),
                label=Path(mount_point).name,
            )
        except OSError:
            return StorageInfo()

    def list_music(self, mount_point: str, music_dir: str = "Music") -> list[dict]:
        results = []
        base = Path(mount_point) / music_dir
        if not base.is_dir():
            base = Path(mount_point)
        try:
            for f in base.rglob("*"):
                if f.is_file() and _is_audio_file(str(f)):
                    rel = f.relative_to(mount_point)
                    results.append({
                        "path": str(f), "relative": str(rel), "name": f.name,
                        "size": f.stat().st_size,
                    })
        except PermissionError:
            pass
        return results

    # ── Pairing ──

    def pair(self, identity: DeviceIdentity) -> dict:
        key = f"{identity.protocol.value}:{identity.serial or identity.mount_point}"
        caps = self.resolve_capabilities(identity)
        with self._lock:
            if key in self._paired:
                return {"ok": False, "error": "ALREADY_PAIRED"}
            self._paired[key] = PairedDevice(
                identity=identity, capabilities=caps,
                paired_at=time.time(), last_contact=time.time(),
            )
        self._notify("paired", {"key": key, "label": identity.label})
        return {"ok": True, "key": key, "label": identity.label}

    def unpair(self, key: str) -> dict:
        with self._lock:
            if key not in self._paired:
                return {"ok": False, "error": "NOT_PAIRED"}
            del self._paired[key]
        self._notify("unpaired", {"key": key})
        return {"ok": True}

    def get_paired(self) -> list[dict]:
        with self._lock:
            return [
                {"key": k, "label": v.identity.label, "vendor": v.identity.vendor,
                 "model": v.identity.model, "protocol": v.identity.protocol.value,
                 "authorized": v.authorized, "trusted": v.trusted,
                 "paired_at": v.paired_at, "last_contact": v.last_contact,
                 "mount_point": v.identity.mount_point}
                for k, v in self._paired.items()
            ]

    def is_paired(self, key: str) -> bool:
        with self._lock:
            return key in self._paired

    # ── Authorization & Trust ──

    def authorize(self, key: str) -> dict:
        with self._lock:
            if key not in self._paired:
                return {"ok": False, "error": "NOT_PAIRED"}
            self._paired[key].authorized = True
        self._notify("authorized", {"key": key})
        return {"ok": True}

    def unauthorize(self, key: str) -> dict:
        with self._lock:
            if key not in self._paired:
                return {"ok": False, "error": "NOT_PAIRED"}
            self._paired[key].authorized = False
        self._notify("unauthorized", {"key": key})
        return {"ok": True}

    def trust(self, key: str) -> dict:
        with self._lock:
            if key not in self._paired:
                return {"ok": False, "error": "NOT_PAIRED"}
            self._paired[key].trusted = True
        self._notify("trusted", {"key": key})
        return {"ok": True}

    def untrust(self, key: str) -> dict:
        with self._lock:
            if key not in self._paired:
                return {"ok": False, "error": "NOT_PAIRED"}
            self._paired[key].trusted = False
        self._notify("untrusted", {"key": key})
        return {"ok": True}

    # ── Transfer jobs ──

    def _next_job_id(self) -> str:
        with self._lock:
            self._job_counter += 1
            return f"sync_{int(time.time())}_{self._job_counter}"

    def create_transfer_job(self, source_path: str, dest_path: str,
                            direction: SyncDirection = SyncDirection.TO_DEVICE) -> TransferJob:
        job_id = self._next_job_id()
        job = TransferJob(
            job_id=job_id, source_path=source_path, dest_path=dest_path,
            direction=direction,
        )
        try:
            job.total_bytes = Path(source_path).stat().st_size
        except OSError:
            job.total_bytes = 0
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> TransferJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, status_filter: TransferStatus | None = None) -> list[TransferJob]:
        with self._lock:
            if status_filter:
                return [j for j in self._jobs.values() if j.status == status_filter]
            return list(self._jobs.values())

    def execute_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        if not job:
            return {"ok": False, "error": "NOT_FOUND"}
        if job.status in (TransferStatus.COMPLETED, TransferStatus.CANCELLED):
            return {"ok": False, "error": "ALREADY_TERMINAL"}
        job.status = TransferStatus.TRANSFERRING
        job.started_at = time.time()
        self._notify("transfer_started", {"job_id": job_id})

        try:
            src = Path(job.source_path)
            dst = Path(job.dest_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            total = job.total_bytes or src.stat().st_size
            transferred = 0
            with open(src, "rb") as fin, open(dst, "wb") as fout:
                while True:
                    if job.cancelled:
                        dst.unlink(missing_ok=True)
                        job.status = TransferStatus.CANCELLED
                        job.finished_at = time.time()
                        self._notify("transfer_cancelled", {"job_id": job_id})
                        self._add_history(job)
                        return {"ok": False, "error": "CANCELLED"}
                    chunk = fin.read(TRANSFER_CHUNK_SIZE)
                    if not chunk:
                        break
                    fout.write(chunk)
                    transferred += len(chunk)
                    job.transferred_bytes = transferred
                    if total > 0 and self._on_progress:
                        job.status = TransferStatus.TRANSFERRING
                        self._on_progress(job)
            job.status = TransferStatus.COMPLETED
            job.transferred_bytes = total
            job.finished_at = time.time()
            self._notify("transfer_completed", {"job_id": job_id})
            self._add_history(job)
            return {"ok": True, "total_bytes": total}
        except OSError as e:
            job.status = TransferStatus.FAILED
            job.error = str(e)
            job.finished_at = time.time()
            self._notify("transfer_failed", {"job_id": job_id, "error": str(e)})
            self._add_history(job)
            return {"ok": False, "error": str(e)}

    def cancel_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        if not job:
            return {"ok": False, "error": "NOT_FOUND"}
        if job.status in (TransferStatus.COMPLETED, TransferStatus.CANCELLED, TransferStatus.FAILED):
            return {"ok": False, "error": "ALREADY_TERMINAL"}
        job.cancelled = True
        job.status = TransferStatus.CANCELLED
        job.finished_at = time.time()
        self._notify("transfer_cancelled", {"job_id": job_id})
        self._add_history(job)
        return {"ok": True}

    def retry_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        if not job:
            return {"ok": False, "error": "NOT_FOUND"}
        job.status = TransferStatus.QUEUED
        job.error = ""
        job.transferred_bytes = 0
        job.started_at = 0.0
        job.finished_at = 0.0
        job.cancelled = False
        self._notify("transfer_retried", {"job_id": job_id})
        return self.execute_job(job_id)

    def _add_history(self, job: TransferJob):
        entry = SyncHistoryEntry(
            job_id=job.job_id, device_label=Path(job.dest_path).parts[0]
            if job.direction == SyncDirection.TO_DEVICE else Path(job.source_path).parts[0],
            timestamp=time.time(), direction=job.direction,
            status=job.status, total_bytes=job.total_bytes,
            transferred_bytes=job.transferred_bytes, error=job.error,
        )
        with self._lock:
            self._history.insert(0, entry)
            if len(self._history) > self._max_history:
                self._history = self._history[:self._max_history]

    def get_history(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return [
                {"job_id": e.job_id, "device": e.device_label,
                 "timestamp": e.timestamp, "direction": e.direction.value,
                 "status": e.status.value, "total_bytes": e.total_bytes,
                 "transferred_bytes": e.transferred_bytes, "error": e.error}
                for e in self._history[:limit]
            ]

    def clear_history(self) -> dict:
        with self._lock:
            self._history.clear()
        return {"ok": True}

    # ── Playlist compatibility ──

    def list_playlists(self, mount_point: str) -> list[dict]:
        results = []
        base = Path(mount_point)
        try:
            for f in base.rglob("*"):
                if f.is_file() and _is_playlist_file(str(f)):
                    results.append({
                        "path": str(f), "name": f.name,
                        "size": f.stat().st_size,
                    })
        except PermissionError:
            pass
        return results

    def free_space(self, mount_point: str) -> dict:
        try:
            st = os.statvfs(mount_point)
            free = st.f_frsize * st.f_bavail
            total = st.f_frsize * st.f_blocks
            return {"ok": True, "free_bytes": free, "total_bytes": total,
                    "free_gb": round(free / (1024**3), 1)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def formats(self) -> list[str]:
        return [".flac", ".mp3", ".wav", ".ogg", ".opus", ".m4a", ".aiff"]

    def profiles(self) -> list[dict]:
        return [
            {"id": "lossless", "name": "Lossless", "format": "flac", "bitrate": 0},
            {"id": "high", "name": "High Quality", "format": "mp3", "bitrate": 320},
            {"id": "medium", "name": "Medium", "format": "mp3", "bitrate": 192},
        ]

    def selection(self, device_key: str) -> dict:
        return {"ok": True, "device_key": device_key, "selected": []}

    def transcode_policy(self, policy: str = "copy") -> dict:
        return {"ok": True, "policy": policy}

    def naming_policy(self, policy: str = "keep") -> dict:
        return {"ok": True, "policy": policy}

    def collision_policy(self, policy: str = "skip") -> dict:
        return {"ok": True, "policy": policy}

    def sync_plan(self, device_key: str) -> dict:
        return {"ok": True, "device_key": device_key, "plan": {
            "total_tracks": 0, "total_size_mb": 0, "new_tracks": 0,
            "existing_tracks": 0, "skipped_tracks": 0}}

    def size_estimate(self, device_key: str, track_count: int) -> dict:
        return {"ok": True, "estimated_mb": track_count * 10}

    def partial_success(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"ok": False, "error": "NOT_FOUND"}
            completed = sum(1 for t in job.transferred if t.status == TransferStatus.COMPLETED)
            failed = sum(1 for t in job.transferred if t.status == TransferStatus.FAILED)
            return {"ok": True, "completed": completed, "failed": failed, "total": len(job.transferred)}

    def eject(self, mount_point: str) -> dict:
        try:
            import subprocess
            subprocess.run(["umount", mount_point], check=False)
            return {"ok": True, "message": f"Unmounted {mount_point}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def start_sync(self, device_key: str, plan: dict | None = None) -> dict:
        return {"ok": True, "message": "Sync started (adapter deferred)", "device_key": device_key}

    def cancel_sync(self, job_id: str = "") -> dict:
        with self._lock:
            cancelled = []
            for jid, job in list(self._jobs.items()):
                if (not job_id or jid == job_id) and job.status in (TransferStatus.QUEUED, TransferStatus.TRANSFERRING):
                    job.status = TransferStatus.CANCELLED
                    cancelled.append(jid)
            return {"ok": True, "cancelled": cancelled}

    def render_playlist(self, playlist_path: str, tracks: list[str]) -> dict:
        try:
            dst = Path(playlist_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            lines = ["#EXTM3U\n"]
            for t in tracks:
                lines.append(f"{t}\n")
            dst.write_text("".join(lines), encoding="utf-8")
            return {"ok": True, "path": str(dst), "count": len(tracks)}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    # ── Errors ──

    def last_errors(self, limit: int = 10) -> list[dict]:
        with self._lock:
            errors = []
            for j in reversed(list(self._jobs.values())):
                if j.error and len(errors) < limit:
                    errors.append({
                        "job_id": j.job_id, "error": j.error,
                        "status": j.status.value, "timestamp": j.finished_at,
                    })
            return errors
