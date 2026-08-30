"""Application ports — library scanner interface and catalog boundary."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from michi.domain.library import LibraryDiagnosticCode
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    TrackRecord,
)


class LibraryFilesystemError(RuntimeError):
    """Raised by the scanner when a filesystem operation cannot be performed.

    Carries a typed diagnostic code so the application layer can degrade
    gracefully instead of propagating raw OSErrors.
    """

    def __init__(
        self, code: LibraryDiagnosticCode, path: Path, detail: str = ""
    ) -> None:
        self.code = code
        self.path = path
        self.detail = detail
        super().__init__(detail or str(path))


class LibraryCatalogError(RuntimeError):
    """Base class for authoritative catalog failures (M6-EXT-R4).

    Authoritative operations either commit or raise — never log-and-succeed.
    """


class LibraryCatalogStorageError(LibraryCatalogError):
    """A catalog write/read failed at the storage level.

    Authoritative operation success means the write committed; storage
    failures surface here instead of being swallowed.
    """


class LibraryCatalogSchemaError(LibraryCatalogError):
    """The catalog database shape is unusable: future version, malformed
    version, or missing authoritative tables. Fail closed — never recreate
    missing authoritative tables empty."""


class LibraryCatalogPort(ABC):
    """Authoritative catalog boundary (M6-EXT-R4).

    The catalog (sources / media files / tracks / stable identities) is USER
    AUTHORITY and is deliberately separate from the rebuildable library
    index cache. Implementations MUST fail closed on schema problems and MUST
    surface storage failures as ``LibraryCatalogStorageError`` (never
    log-and-return-success).
    """

    @abstractmethod
    def schema_version(self) -> int: ...

    @abstractmethod
    def load_sources(self) -> tuple[LibrarySource, ...]: ...

    @abstractmethod
    def load_media(self) -> tuple[MediaFileRecord, ...]: ...

    @abstractmethod
    def load_tracks(self) -> tuple[TrackRecord, ...]: ...

    @abstractmethod
    def media_for_source(self, source_id: str) -> tuple[MediaFileRecord, ...]: ...

    @abstractmethod
    def get_track(self, track_id: str) -> TrackRecord | None:
        """Single TrackRecord by stable identity (efficient lookup)."""

    @abstractmethod
    def get_media(self, media_file_id: str) -> MediaFileRecord | None:
        """Single MediaFileRecord by stable identity (efficient lookup)."""

    @abstractmethod
    def upsert_source(self, source: LibrarySource) -> None: ...

    @abstractmethod
    def set_source_enabled(self, source_id: str, enabled: bool) -> None: ...

    @abstractmethod
    def retire_source(self, source_id: str) -> None: ...

    @abstractmethod
    def upsert_media(self, records: tuple[MediaFileRecord, ...]) -> None: ...

    @abstractmethod
    def mark_media_availability(
        self, media_id: str, availability: MediaAvailability
    ) -> None: ...

    @abstractmethod
    def upsert_tracks(self, tracks: tuple[TrackRecord, ...]) -> None: ...

    @abstractmethod
    def apply_source_reconciliation(
        self,
        media_records: tuple[MediaFileRecord, ...],
        track_records: tuple[TrackRecord, ...],
    ) -> None:
        """ATOMIC authoritative source reconciliation (M6-EXT-R4 freeze gate).

        Media AND track mutations land in ONE transaction: a media row can
        never exist without its TrackRecord (identity atomicity). Any
        failure rolls back EVERYTHING — partial authoritative state is
        impossible by construction. The coordinator calls this once per
        scan, then updates rebuildable caches, then publishes LibraryState.
        """


class LibraryUserStatePort(ABC):
    """Authoritative favorites/history/recently-added persistence by TrackId
    (M6-EXT-R4-G). Truthful writes: operations either commit or raise
    ``LibraryCatalogStorageError`` — never log-and-return-success.

    The application layer owns semantics (sorted favorites, history
    consecutive-dedupe + cap, recently-added cap); this boundary persists
    ordered TrackId collections atomically.
    """

    @abstractmethod
    def load_favorites(self) -> tuple[str, ...]: ...

    @abstractmethod
    def set_favorites(self, track_ids: tuple[str, ...]) -> None: ...

    @abstractmethod
    def load_history(self) -> tuple[str, ...]: ...

    @abstractmethod
    def set_history(self, track_ids: tuple[str, ...]) -> None: ...

    @abstractmethod
    def load_recently_added(self) -> tuple[str, ...]: ...

    @abstractmethod
    def set_recently_added(self, track_ids: tuple[str, ...]) -> None: ...


# ONE supported-media policy (M6-EXT-R4 freeze gate §23): the pre-R4
# contract set. R4 is Library Resilience — NOT a format expansion program.
# A file outside this set is never catalogued by the source scanner.
SUPPORTED_MEDIA_SUFFIXES = frozenset(
    {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}
)


@dataclass(frozen=True)
class DiscoveredMediaFile:
    """One filesystem discovery fact (M6-EXT-R4-K).

    The scanner discovers FILESYSTEM FACTS ONLY: absolute path, validated
    relative path inside the source, fingerprint. It never allocates
    TrackIds and never mutates the catalog."""

    absolute_path: Path
    relative_path: str
    file_size: int
    mtime_ns: int
    device_id: int = 0
    inode: int = 0


class LibrarySourceScannerPort(ABC):
    """Source-aware scanner boundary (M6-EXT-R4-K).

    ``discover`` enumerates ONE source root. Directory symlinks are NOT
    recursively followed (cycles / duplicate traversal / source escapes are
    forbidden by contract). Raises ``LibraryFilesystemError`` with a typed
    code when the root cannot be enumerated."""

    @abstractmethod
    def discover(self, source: LibrarySource) -> tuple[DiscoveredMediaFile, ...]:
        """Enumerate media facts inside the source root.

        The returned relative paths are validated (never absolute, never
        ``..``-escaping, always inside the source)."""

    def discover_cancellable(
        self,
        source: LibrarySource,
        token=None,
        on_entry=None,
    ) -> tuple[DiscoveredMediaFile, ...]:
        """OPTIONAL cooperative-cancellation capability (CONCURRENCY-LIB-03):
        default = plain discover for legacy fakes. The production scanner
        overrides this with a cancellable walk."""
        del token, on_entry
        return self.discover(source)

    @abstractmethod
    def validate_file(self, path: Path) -> None:
        """Raise LibraryFilesystemError when ``path`` is not a playable file."""


class LibraryScannerPort(ABC):
    """Abstract library scanner. Infrastructure implements filesystem access."""

    @abstractmethod
    def scan(self, root: Path) -> list[Path]: ...

    @abstractmethod
    def fingerprint(self, path: Path) -> tuple[int, int]:
        """Filesystem fingerprint (file_size, mtime_ns) for incremental
        scans; raises LibraryFilesystemError on failure (typed)."""

    @abstractmethod
    def validate_file(self, path: Path) -> None:
        """Raise LibraryFilesystemError when ``path`` is not a playable file."""
