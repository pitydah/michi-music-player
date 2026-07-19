"""Compatibility facade for the canonical vinyl recorder.

New code should import from :mod:`vinyl.vinyl_recorder_service`. This module
keeps the historical Audio Lab import path stable.
"""

from vinyl.vinyl_recorder_service import (
    ADCRecorderService,
    AudioDevice,
    USBTurntableDetector,
    VinylRecorderService,
)
from vinyl.vinyl_types import CaptureRequest, RecordingSession, StereoLevels

__all__ = [
    "ADCRecorderService",
    "VinylRecorderService",
    "AudioDevice",
    "RecordingSession",
    "StereoLevels",
    "CaptureRequest",
    "USBTurntableDetector",
]
