"""Canonical data types for vinyl capture, projects, and exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RecordingStatus(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    RECORDING_SIDE_A = "recording_side_a"
    RECORDING_SIDE_B = "recording_side_b"
    SPLITTING = "splitting"
    CLEANING = "cleaning"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class CaptureDevice:
    """Capture endpoint exposed by a concrete audio backend.

    Legacy ``device_id``, ``channels`` and ``sample_rate`` attributes remain
    available because the QML bridge and older tests still use them. ``source``
    is the backend-native identifier, such as ``hw:1,0`` on ALSA.
    """

    device_id: int = 0
    name: str = ""
    description: str = ""
    backend: str = "ffmpeg"
    source: str = ""
    is_usb: bool = False
    is_turntable: bool = False
    brand: str | None = None
    sample_rates: list[int] = field(
        default_factory=lambda: [44100, 48000, 88200, 96000]
    )
    bit_depths: list[int] = field(default_factory=lambda: [16, 24, 32])
    channels: int = 2
    sample_rate: int = 44100
    channel_counts: list[int] = field(default_factory=lambda: [1, 2])
    is_default: bool = False

    def __post_init__(self) -> None:
        if not self.source:
            self.source = str(self.device_id)
        if self.sample_rate and self.sample_rate not in self.sample_rates:
            self.sample_rates.insert(0, self.sample_rate)
        if self.channels and self.channels not in self.channel_counts:
            self.channel_counts.append(self.channels)

    @property
    def id(self) -> str:
        return str(self.device_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "backend": self.backend,
            "source": self.source,
            "is_usb": self.is_usb,
            "is_turntable": self.is_turntable,
            "brand": self.brand,
            "sample_rates": list(self.sample_rates),
            "bit_depths": list(self.bit_depths),
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "channel_counts": list(self.channel_counts),
            "is_default": self.is_default,
        }


@dataclass
class StereoLevels:
    left_peak_dbfs: float = -60.0
    right_peak_dbfs: float = -60.0
    left_rms_dbfs: float = -60.0
    right_rms_dbfs: float = -60.0
    clipping_left: bool = False
    clipping_right: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_peak_dbfs": self.left_peak_dbfs,
            "right_peak_dbfs": self.right_peak_dbfs,
            "left_rms_dbfs": self.left_rms_dbfs,
            "right_rms_dbfs": self.right_rms_dbfs,
            "clipping_left": self.clipping_left,
            "clipping_right": self.clipping_right,
        }


@dataclass
class CaptureRequest:
    device: CaptureDevice
    output_path: str
    format: str = "wav"
    sample_rate: int = 44100
    bit_depth: int = 24
    channels: int = 2
    dsp_filters: list[str] = field(default_factory=list)


@dataclass
class RecordingSession:
    session_id: str = ""
    input_device: CaptureDevice = field(default_factory=CaptureDevice)
    output_path: str = ""
    format: str = "wav"
    sample_rate: int = 44100
    bit_depth: int = 24
    channels: int = 2
    start_time: float = 0.0
    end_time: float | None = None
    duration: float = 0.0
    file_size: int = 0
    markers: list[dict[str, Any]] = field(default_factory=list)
    status: str = RecordingStatus.IDLE.value
    paused_at: float | None = None
    total_paused: float = 0.0
    error: str = ""
    levels: StereoLevels = field(default_factory=StereoLevels)


@dataclass
class VinylProject:
    id: str = ""
    name: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    artist: str = ""
    album: str = ""
    year: int = 0
    genre: str = ""
    side_a_path: str = ""
    side_b_path: str = ""
    sample_rate: int = 96000
    bit_depth: int = 24
    channels: int = 2
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TrackSplit:
    id: str = ""
    project_id: str = ""
    side: str = "A"
    track_number: int = 0
    title: str = ""
    start_sec: float = 0.0
    end_sec: float = 0.0
    duration_sec: float = 0.0
    artist: str = ""


@dataclass
class WaveformCache:
    project_id: str = ""
    side: str = "A"
    data: list[float] = field(default_factory=list)
    peaks: list[float] = field(default_factory=list)
    sample_count: int = 0
    duration_sec: float = 0.0
