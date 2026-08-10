"""Domain layer — pure business logic. No Qt, no infrastructure."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


class PlaybackStatus(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


@dataclass
class PlaybackState:
    """Single canonical authority for playback state. No Qt dependency."""

    status: PlaybackStatus = PlaybackStatus.STOPPED
    file_path: Path | None = None
    position_ms: int = 0
    duration_ms: int = 0
    volume: int = 100  # 0-100
    muted: bool = False
    error_message: str | None = None
