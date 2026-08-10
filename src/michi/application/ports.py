"""Application layer — use cases and ports. Depends on Domain only."""

from abc import ABC, abstractmethod
from collections.abc import Callable
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

    @abstractmethod
    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the current media finishes."""
        ...

    @abstractmethod
    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        """Remove a previously registered end-of-media callback."""
        ...

    @abstractmethod
    def subscribe_position_changed(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback invoked with (position_ms, duration_ms)."""
        ...

    @abstractmethod
    def unsubscribe_position_changed(
        self, callback: Callable[[int, int], None]
    ) -> None:
        """Remove a previously registered position-changed callback."""
        ...

    @abstractmethod
    def subscribe_error(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked with an error message string."""
        ...

    @abstractmethod
    def unsubscribe_error(self, callback: Callable[[str], None]) -> None:
        """Remove a previously registered error callback."""
        ...
