"""Job type definitions for the unified job system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    QUALITY_ANALYSIS = "quality_analysis"
    SPECTRAL_ANALYSIS = "spectral_analysis"
    FEATURE_EXTRACTION = "feature_extraction"
    SIMILARITY_INDEX = "similarity_index"
    LIBRARY_VERIFY = "library_verify"
    CONVERSION = "conversion"
    RIPPING = "ripping"
    VINYL_RECORDING = "vinyl_recording"
    VINYL_WAVEFORM_BUILD = "vinyl_waveform_build"
    VINYL_SILENCE_DETECTION = "vinyl_silence_detection"
    VINYL_EXPORT = "vinyl_export"
    VINYL_IMPORT = "vinyl_import"


@dataclass
class Job:
    id: str = ""
    type: JobType = JobType.QUALITY_ANALYSIS
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    label: str = ""
    entity_type: str = ""       # "track", "album", "file", "project"
    entity_id: str = ""         # track uri, album key, filepath, project id
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    log: list[str] = field(default_factory=list)
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    retry_count: int = 0
    max_retries: int = 2
    cancellable: bool = True
    pausable: bool = False
