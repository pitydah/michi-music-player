"""Device sync domain models — identity, capabilities, plans, outcomes.

These dataclasses are the canonical domain types for the device sync
pipeline (Fase Sync, P0 stabilization). They are re-exported by the
``core.device_sync_service`` facade for backward-compatible imports.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".wv", ".ogg", ".opus", ".m4a", ".aac",
    ".wma", ".dsf", ".dff", ".ape", ".aiff", ".aif", ".mpc",
})

AUDIO_PLAYLIST_EXTENSIONS = frozenset({".m3u", ".m3u8", ".pls", ".xspf"})


class DeviceProtocol(Enum):
    """Transport protocol of a detected device.

    Protocols are decided by the discovery adapters (MSC mount, MTP,
    Michi Link, network filesystem) — never by brand-name detection.
    ``GENERIC_DEDICATED`` is kept for backward compatibility and is
    treated as a capability profile hint, not a protocol core.
    """

    ANDROID_MTP = "android_mtp"
    USB_MASS_STORAGE = "usb_mass_storage"
    GENERIC_DEDICATED = "generic_dedicated"
    MICHI_LINK = "michi_link"
    NETWORK_FILESYSTEM = "network_filesystem"
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


class SyncErrorCode(str, Enum):
    """Explicit failure codes for the sync pipeline (no falso éxito)."""

    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    SPACE_INSUFFICIENT = "SPACE_INSUFFICIENT"
    FORMAT_UNSUPPORTED = "FORMAT_UNSUPPORTED"
    PLAN_EMPTY = "PLAN_EMPTY"
    TRANSFER_FAILED = "TRANSFER_FAILED"
    VERIFICATION_MISMATCH = "VERIFICATION_MISMATCH"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    CANCELLED = "CANCELLED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    NO_TRACKS = "NO_TRACKS"


class IdentitySource(str, Enum):
    """Which step of the identity priority chain produced the serial."""

    USB_SERIAL = "usb_serial"
    MTP_ID = "mtp_id"
    FILESYSTEM_UUID = "filesystem_uuid"
    VENDOR_PRODUCT_VOLUME_UUID = "vendor_product_volume_uuid"
    PERSISTED_FINGERPRINT = "persisted_fingerprint"
    UNSTABLE_FALLBACK = "unstable_fallback"


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
    identity_source: str = ""
    identity_unstable: bool = False


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
class DeviceInfo:
    """Adapter-level detection result with the full identity candidate set.

    The stable serial is resolved from these candidates by the identity
    priority chain (``core.device_sync.identity.resolve_identity``):
    USB serial → MTP persistent ID → filesystem UUID → vendor/product/
    volume UUID → persisted fingerprint → explicit unstable fallback.
    """

    protocol: DeviceProtocol = DeviceProtocol.UNKNOWN
    label: str = ""
    mount_point: str = ""
    vendor: str = ""
    model: str = ""
    usb_serial: str = ""
    mtp_id: str = ""
    filesystem_uuid: str = ""
    volume_uuid: str = ""
    volume_label: str = ""
    music_directory: str = "Music"
    free_bytes: int = 0
    total_bytes: int = 0
    capabilities: list = field(default_factory=list)
    declared_formats: set | None = None
    serial: str = ""
    identity_source: str = ""
    identity_unstable: bool = False
    fingerprint: str = ""


@dataclass
class SyncPlanItem:
    source: str = ""
    dest: str = ""
    action: str = "copy"  # copy | transcode
    size_bytes: int = 0
    target_ext: str = ""
    transcode_profile: str = ""
    reason: str = ""


@dataclass
class DeviceSyncPlan:
    device_id: str = ""
    items: list = field(default_factory=list)
    total_bytes: int = 0
    free_bytes: int = 0
    needed_bytes: int = 0
    can_fit: bool = False
    error_code: str = ""
    error: str = ""


@dataclass
class TransferOutcome:
    ok: bool = False
    status: str = TransferStatus.FAILED.value
    bytes_transferred: int = 0
    error: str = ""
    error_code: str = ""


@dataclass
class VerificationResult:
    ok: bool = False
    size_match: bool = False
    checksum_match: bool = False
    source_checksum: str = ""
    dest_checksum: str = ""


@dataclass
class TransferJob:
    """Read-only projection of a durable job (never a parallel registry).

    Built from ``DurableJobService`` state; source/destination paths come
    from the job payload. The facade never stores jobs itself.
    """

    job_id: str = ""
    source_path: str = ""
    dest_path: str = ""
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
    job_id: str = ""
    device_label: str = ""
    device_id: str = ""
    timestamp: float = 0.0
    direction: SyncDirection = SyncDirection.TO_DEVICE
    status: TransferStatus = TransferStatus.COMPLETED
    total_bytes: int = 0
    transferred_bytes: int = 0
    error: str = ""
    playlist_path: str = ""


@dataclass
class PairedDevice:
    identity: DeviceIdentity | None = None
    capabilities: DeviceCapabilities | None = None
    authorized: bool = False
    trusted: bool = False
    paired_at: float = 0.0
    last_contact: float = 0.0


def is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def is_playlist_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_PLAYLIST_EXTENSIONS


def safe_filename(name: str, max_len: int = 255) -> str:
    safe = "".join(c if c.isalnum() or c in " ._-()[]" else "_" for c in name)
    if len(safe) > max_len:
        base, ext = os.path.splitext(safe)
        safe = base[: max_len - len(ext)] + ext
    return safe


def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1048576:
        return f"{bytes_val / 1024:.1f} KB"
    if bytes_val < 1073741824:
        return f"{bytes_val / 1048576:.1f} MB"
    return f"{bytes_val / 1073741824:.2f} GB"
