"""Application layer — use cases and ports. Depends on Domain only."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from michi.domain.library import Artwork, LibraryPrefs, TrackMetadata
from michi.domain.library_index import LibraryIndexEntry
from michi.domain.playback import PlaybackStatus
from michi.domain.playlist import Playlist, PlaylistNavigationState
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

    def get_embedded_front_artwork(self, file_path: Path) -> Artwork | None:
        """EXPLICIT front-cover-only embedded artwork (M6-PRODUCTION-
        INTEGRATION): the album-level resolution needs to distinguish
        'explicit FRONT' from 'any embedded'. Default: None (no
        differentiation) — providers that cannot distinguish fall back to
        the generic embedded lookup."""
        return None

    @abstractmethod
    def get_local_artwork(self, album_dir: Path) -> Artwork | None:
        """Deterministic local fallback in the album directory (M6.5):
        cover.* / folder.* / front.* — unreadable entries skipped."""


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
    """Playlist persistence (best effort; load never raises).

    M8-R1: playlists persist with stable ids (V2); legacy V1 records decode
    to deterministic ids. Navigation metadata (pinned/recent) has its own
    load/save pair. Default no-op implementations keep existing fakes and
    optional wiring backward compatible."""

    @abstractmethod
    def load(self) -> tuple[Playlist, ...]: ...

    @abstractmethod
    def save(self, playlists: tuple[Playlist, ...]) -> None: ...

    def load_navigation(self) -> "PlaylistNavigationState":
        """Pinned/recent state; optional key — absence degrades to empty."""
        return PlaylistNavigationState()

    def save_navigation(self, state: "PlaylistNavigationState") -> None:
        """Best-effort persistence of pinned/recent state; default no-op.

        Concrete no-op (not abstract): legacy fakes and optional wiring stay
        backward compatible without implementing navigation persistence."""
        del state  # default no-op: navigation persistence is optional


class PlaylistArtworkStorePort(ABC):
    """Boundary for user-supplied playlist artwork storage (M9-R2.1).
    Managed copies reside inside application data storage."""

    @abstractmethod
    def store_cover(self, playlist_id: str, source_path: Path | str) -> str | None:
        """Copies source image atomically to managed storage. Returns managed path."""
        ...

    @abstractmethod
    def delete_cover(self, playlist_id: str) -> None:
        """Deletes any managed cover file for the given playlist id."""
        ...


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
    def save(self, snapshot: PlaybackSessionSnapshot) -> bool:
        """Persist the snapshot; never raises.

        Returns the success signal the application decides on:
        True = the snapshot was durably persisted; False = it was not
        persisted (the repository logged the failure). The application
        advances its durable-state marker only on True.
        """


class LibraryIndexRepository(ABC):
    """Persistent library index (M6.2) — bounded context, best effort.

    The filesystem is the truth about physical existence; this repository
    only persists cached knowledge. Never raises: sqlite errors are logged.
    """

    @abstractmethod
    def load_all(self) -> tuple[LibraryIndexEntry, ...]: ...

    @abstractmethod
    def upsert_many(self, entries) -> None: ...

    @abstractmethod
    def remove(self, track_id: str) -> None: ...

    @abstractmethod
    def apply_delta(self, upserts, removed) -> None:
        """All-or-nothing durable index mutation (M6-PRODUCTION-INTEGRATION):
        the upserts AND removes land in ONE transaction. The application
        calls this ONLY after the generation gate on the owner thread — a
        stale/closed generation can never leave a partially-applied index.
        Never raises: sqlite errors are logged."""

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def version(self) -> int: ...


class ScanProgress:
    """Mutable cross-thread scan progress (M6.4). The worker updates the
    fields and reports; the owner maps them onto LibraryState.

    M6-FINAL-CROSS-PERSISTENCE-GATE: the mutable builder stays WORKER-LOCAL;
    every emission transports a fresh immutable ``ScanProgressSnapshot`` so
    the owner thread never observes a mutating object."""

    def __init__(self) -> None:
        self.phase: str | None = None
        self.current_path: str | None = None
        self.processed: int = 0
        self.total: int = 0


@dataclass(frozen=True)
class ScanProgressSnapshot:
    """Immutable progress snapshot crossing the thread boundary.

    The worker owns the mutable builder; the runner snapshots it at every
    report() so the Qt signal and the owner thread see stable values that
    can never be mutated by later progress (M6-FINAL-CROSS-PERSISTENCE)."""

    phase: str | None = None
    current_path: str | None = None
    processed: int = 0
    total: int = 0

    @classmethod
    def from_progress(cls, progress: ScanProgress) -> "ScanProgressSnapshot":
        return cls(
            phase=progress.phase,
            current_path=progress.current_path,
            processed=progress.processed,
            total=progress.total,
        )


class ScanCancelToken:
    """Cooperative cancellation flag (M6.4). The worker checks it between
    tracks and raises ScanCancelled."""

    def __init__(self) -> None:
        self.cancelled: bool = False


class ScanCancelled(Exception):  # noqa: N818 — name pinned by the M6.4 contract
    """Cooperative cancellation signal (M6.4)."""


class ScanPipelinePort(ABC):
    """Async scan runner boundary (M6.4). The heavy scan work runs off the
    UI thread; progress/done are dispatched to the owner thread.

    Contract shapes:
    - work = Callable[[ScanProgress, ScanCancelToken, Callable[[], None]], ScanResult]
    - on_progress = Callable[[ScanProgress], None]
    - on_done = Callable[[int, ScanResult | None, BaseException | None], None]
    """

    @abstractmethod
    def submit(self, generation: int, work, on_progress, on_done) -> None: ...

    @abstractmethod
    def cancel(self, generation: int) -> None: ...
