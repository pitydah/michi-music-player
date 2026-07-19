"""Vinyl capture and digitisation subsystem."""

from .vinyl_recorder_service import (
    ADCRecorderService,
    AudioDevice,
    USBTurntableDetector,
    VinylRecorderService,
)
from .vinyl_types import (
    CaptureDevice,
    CaptureRequest,
    ProjectStatus,
    RecordingSession,
    RecordingStatus,
    StereoLevels,
    TrackSplit,
    VinylProject,
    WaveformCache,
)

__all__ = [
    "ADCRecorderService",
    "AudioDevice",
    "USBTurntableDetector",
    "VinylRecorderService",
    "CaptureDevice",
    "CaptureRequest",
    "ProjectStatus",
    "RecordingSession",
    "RecordingStatus",
    "StereoLevels",
    "TrackSplit",
    "VinylProject",
    "WaveformCache",
]
