"""Application layer — use cases and ports. Depends on Domain only."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from michi.domain.playback import PlaybackStatus


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
    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None: ...

    @abstractmethod
    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None: ...

    @abstractmethod
    def subscribe_position_changed(self, callback: Callable[[int], None]) -> None: ...

    @abstractmethod
    def unsubscribe_position_changed(self, callback: Callable[[int], None]) -> None: ...

    @abstractmethod
    def subscribe_duration_changed(self, callback: Callable[[int], None]) -> None: ...

    @abstractmethod
    def unsubscribe_duration_changed(self, callback: Callable[[int], None]) -> None: ...

    @abstractmethod
    def subscribe_media_accepted(self, callback: Callable[[Path], None]) -> None: ...

    @abstractmethod
    def unsubscribe_media_accepted(self, callback: Callable[[Path], None]) -> None: ...

    @abstractmethod
    def subscribe_media_rejected(
        self, callback: Callable[[Path, str], None]
    ) -> None: ...

    @abstractmethod
    def unsubscribe_media_rejected(
        self, callback: Callable[[Path, str], None]
    ) -> None: ...

    @abstractmethod
    def subscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None: ...

    @abstractmethod
    def unsubscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None: ...
