"""Application layer — use cases and ports. Depends on Domain only."""

from abc import ABC, abstractmethod
from pathlib import Path


class AudioPort(ABC):
    """Abstract audio backend. Infrastructure implements this."""

    @abstractmethod
    def load(self, file_path: Path) -> None: ...

    @abstractmethod
    def play(self) -> None: ...

    @abstractmethod
    def pause(self) -> None: ...

    @abstractmethod
    def resume(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def set_volume(self, value: int) -> None: ...

    @abstractmethod
    def set_muted(self, muted: bool) -> None: ...

    @abstractmethod
    def seek(self, position_ms: int) -> None: ...

    @abstractmethod
    def position(self) -> int: ...

    @abstractmethod
    def duration(self) -> int: ...
