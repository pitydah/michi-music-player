"""Index state — tracks scan progress, stats, and phase."""
import time
from dataclasses import dataclass
from enum import Enum


class ScanPhase(Enum):
    IDLE = "idle"
    WALKING = "walking"
    DETECTING = "detecting"
    EXTRACTING = "extracting"
    WRITING = "writing"
    CLEANING = "cleaning"
    REBUILDING = "rebuilding"
    ENRICHING = "enriching"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class ScanState:
    phase: ScanPhase = ScanPhase.IDLE
    root_path: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    file_count: int = 0
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    missing_count: int = 0

    current_file: str = ""
    progress_pct: float = 0.0

    cancelled: bool = False

    def start(self, root_path: str, file_count: int = 0):
        self.phase = ScanPhase.WALKING
        self.root_path = root_path
        self.started_at = time.time()
        self.file_count = file_count
        self.added_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.missing_count = 0
        self.cancelled = False
        self.progress_pct = 0.0

    def finish(self, phase: ScanPhase = ScanPhase.DONE):
        self.phase = phase
        self.finished_at = time.time()
        self.progress_pct = 100.0

    def cancel(self):
        self.cancelled = True
        self.phase = ScanPhase.CANCELLED
        self.finished_at = time.time()

    @property
    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.finished_at or time.time()
        return end - self.started_at

    @property
    def files_per_second(self) -> float:
        if self.elapsed <= 0:
            return 0.0
        return (self.added_count + self.updated_count) / self.elapsed

    @property
    def total_processed(self) -> int:
        return self.added_count + self.updated_count + self.skipped_count

    def set_phase(self, phase: ScanPhase):
        self.phase = phase

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "root_path": self.root_path,
            "file_count": self.file_count,
            "added": self.added_count,
            "updated": self.updated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
            "missing": self.missing_count,
            "total_processed": self.total_processed,
            "elapsed": round(self.elapsed, 1),
            "files_per_second": round(self.files_per_second, 1),
            "progress": round(self.progress_pct, 1),
        }
