"""Transport adapters for device synchronization.
Each transport handles a specific protocol (UMS, MTP, AndroidMichi).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DeviceCapability(Enum):
    AUDIO_PLAYBACK = "audio_playback"
    STORAGE_UMS = "storage_ums"
    STORAGE_MTP = "storage_mtp"
    STORAGE_NETWORK = "storage_network"
    PLAYLIST_M3U = "playlist_m3u"
    PLAYLIST_PLS = "playlist_pls"
    METADATA_READ = "metadata_read"
    METADATA_WRITE = "metadata_write"
    COVER_ART = "cover_art"
    TRANSCODING = "transcoding"
    SYNC_PARTIAL = "sync_partial"
    BATTERY_MONITOR = "battery_monitor"


@dataclass
class DeviceInfo:
    device_id: str
    name: str
    manufacturer: str = ""
    model: str = ""
    serial: str = ""
    protocols: list[str] = field(default_factory=list)
    storage_total: int = 0
    storage_free: int = 0
    audio_formats: list[str] = field(default_factory=lambda: ["mp3", "flac", "ogg", "wav", "m4a"])
    playlist_formats: list[str] = field(default_factory=lambda: ["m3u", "m3u8", "pls"])
    max_filename_length: int = 255
    max_path_length: int = 512
    supports_cover_art: bool = False
    supports_playlists: bool = True
    supports_metadata_write: bool = False
    filesystem_case_sensitive: bool = True


@dataclass
class TransferPlan:
    """Result of comparing local selection with device contents."""
    to_copy: list[Path] = field(default_factory=list)
    to_update: list[Path] = field(default_factory=list)
    to_skip: list[Path] = field(default_factory=list)
    to_transcode: list[tuple[Path, str]] = field(default_factory=list)
    to_delete: list[Path] = field(default_factory=list)
    conflicts: list[Path] = field(default_factory=list)
    total_bytes: int = 0
    estimated_time_s: int = 0


class DeviceTransport(ABC):
    """Abstract base for all device transport protocols."""

    @abstractmethod
    def discover(self) -> list[DeviceInfo]:
        """Discover available devices."""
        ...

    @abstractmethod
    def connect(self, device_id: str) -> bool:
        """Connect to a specific device."""
        ...

    @abstractmethod
    def disconnect(self, device_id: str) -> bool:
        """Disconnect from a device."""
        ...

    @abstractmethod
    def list_storage(self, device_id: str) -> list[dict]:
        """List storage volumes on device."""
        ...

    @abstractmethod
    def list_files(self, device_id: str, path: str) -> list[dict]:
        """List files in a directory on the device."""
        ...

    @abstractmethod
    def get_device_info(self, device_id: str) -> DeviceInfo:
        """Get detailed device information."""
        ...

    def create_plan(self, local_files: list[Path], device_files: list[dict],
                    device_info: DeviceInfo, music_dir: str = "Music") -> TransferPlan:
        """Compare local selection with device contents and create transfer plan."""
        plan = TransferPlan()
        device_paths = {f.get('path', ''): f for f in device_files}

        for local_path in local_files:
            dest_name = f"{music_dir}/{local_path.name}"

            if local_path.suffix.lower().lstrip('.') not in device_info.audio_formats:
                # Check if transcode needed
                plan.to_transcode.append((local_path, 'mp3'))
                continue

            if dest_name in device_paths:
                dev_file = device_paths[dest_name]
                local_size = local_path.stat().st_size
                dev_size = dev_file.get('size', 0)
                if local_size == dev_size:
                    plan.to_skip.append(local_path)
                else:
                    plan.to_update.append(local_path)
            else:
                plan.to_copy.append(local_path)

        return plan
