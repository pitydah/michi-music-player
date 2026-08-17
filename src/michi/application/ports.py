"""Application layer — use cases and ports. Depends on Domain only."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from michi.domain.library import Artwork, LibraryPrefs, TrackMetadata
from michi.domain.playback import PlaybackStatus
from michi.domain.playlist import Playlist
from michi.domain.session import PlaybackSessionSnapshot


class MetadataExtractionError(RuntimeError):
    """A media file could not be read for metadata extraction (filesystem-
    level failure: missing, unreadable, vanished mid-read)."""

    def __init__(self, path: Path, detail: str = "") -> None:
        super().__init__(detail or str(path))
        self.path = path
        self.detail = detail


class MetadataExtractorPort(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> TrackMetadata: ...


class ArtworkProviderPort(ABC):
    """Reads embedded cover art from media files.

    Artwork absence is NOT an error: untagged, corrupt or unreadable files
    yield ``None`` (the implementation logs and returns None instead of
    raising)."""

    @abstractmethod
    def get_embedded_artwork(self, file_path: Path) -> Artwork | None: ...


class ArtworkCachePort(ABC):
    """Artwork cache boundary (best effort; infrastructure owns the disk)."""

    @abstractmethod
    def store(self, album_key: str, artwork: "Artwork") -> Path | None: ...


class LibraryPrefsPort(ABC):
    """Favorites/history/recently-added persistence (best effort)."""

    @abstractmethod
    def load(self) -> "LibraryPrefs": ...

    @abstractmethod
    def save(self, prefs: "LibraryPrefs") -> None: ...


class PlaylistsPort(ABC):
    """Playlist persistence (best effort; load never raises)."""

    @abstractmethod
    def load(self) -> tuple[Playlist, ...]: ...

    @abstractmethod
    def save(self, playlists: tuple[Playlist, ...]) -> None: ...


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


class SessionRepository(ABC):
    """Playback session snapshot persistence (best effort; load never raises).

    A malformed or unreadable persisted snapshot degrades to a fresh
    snapshot (safe read fallback) — load() never raises and never
    overwrites the malformed original data.
    """

    @abstractmethod
    def load(self) -> PlaybackSessionSnapshot: ...

    @abstractmethod
    def save(self, snapshot: PlaybackSessionSnapshot) -> None: ...
