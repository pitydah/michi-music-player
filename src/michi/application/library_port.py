"""Application ports — library scanner interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from michi.domain.library import LibraryDiagnosticCode


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
