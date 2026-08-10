"""Test fixtures for M1-M7 core services."""

import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class FakeAudioPort:
    """Minimal fake for testing — never copied from Legacy."""

    def __init__(self) -> None:
        self.loaded: Path | None = None
        self.state: str = "stopped"
        self.volume: int = 80
        self.muted: bool = False
        self._position: int = 0
        self._duration: int = 0
        self._end_callbacks: list = []

    def load(self, file_path: Path) -> None:
        self.loaded = file_path

    def play(self) -> None:
        self.state = "playing"

    def pause(self) -> None:
        self.state = "paused"

    def resume(self) -> None:
        self.state = "playing"

    def stop(self) -> None:
        self.state = "stopped"

    def set_volume(self, value: int) -> None:
        self.volume = max(0, min(100, value))

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def seek(self, position_ms: int) -> None:
        self._position = position_ms

    def position(self) -> int:
        return self._position

    def duration(self) -> int:
        return self._duration

    def set_duration(self, ms: int) -> None:
        self._duration = ms

    def on_end_of_media(self, callback: Any) -> None:
        self._end_callbacks.append(callback)

    def remove_end_of_media_callbacks(self) -> None:
        self._end_callbacks.clear()

    def trigger_end_of_media(self) -> None:
        for cb in self._end_callbacks:
            cb()


@pytest.fixture
def fake_audio() -> FakeAudioPort:
    return FakeAudioPort()


@pytest.fixture
def playback_service(fake_audio: FakeAudioPort):
    from michi.application.playback_service import PlaybackService
    return PlaybackService(fake_audio)


@pytest.fixture
def queue_service(playback_service):
    from michi.application.queue_service import QueueService
    return QueueService(playback_service)
