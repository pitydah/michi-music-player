"""Filesystem library scanner — implements LibraryScannerPort."""

import errno
import stat
from pathlib import Path

from michi.application.library_port import LibraryFilesystemError, LibraryScannerPort
from michi.domain.library import LibraryDiagnosticCode

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}


def _classify_os_error(exc: OSError, *, root: bool) -> LibraryDiagnosticCode:
    """Map an OSError to the library degradation taxonomy."""
    if exc.errno in (errno.ENOENT, errno.ENOTDIR):
        return (
            LibraryDiagnosticCode.DIRECTORY_MISSING
            if root
            else LibraryDiagnosticCode.TRACK_MISSING
        )
    if exc.errno in (errno.EACCES, errno.EPERM):
        return LibraryDiagnosticCode.ACCESS_FAILURE
    if exc.errno in (errno.EIO, errno.ESTALE, errno.ENODEV):
        return LibraryDiagnosticCode.IO_FAILURE
    return LibraryDiagnosticCode.UNKNOWN_FAILURE


def _classify_traversal_error(exc: OSError) -> LibraryDiagnosticCode:
    """Map a mid-scan traversal OSError to the library degradation taxonomy.

    A directory vanishing mid-scan (ENOENT/ENOTDIR) is an environmental race,
    not a missing track or a missing root, so it falls under UNKNOWN_FAILURE.
    """
    if exc.errno in (errno.EACCES, errno.EPERM):
        return LibraryDiagnosticCode.ACCESS_FAILURE
    if exc.errno in (errno.EIO, errno.ESTALE, errno.ENODEV):
        return LibraryDiagnosticCode.IO_FAILURE
    return LibraryDiagnosticCode.UNKNOWN_FAILURE


class FilesystemLibraryScanner(LibraryScannerPort):
    """Infrastructure adapter: recursively discovers audio files."""

    def _raise_fs_error(self, code, path, detail=""):
        raise LibraryFilesystemError(code, path, detail)

    def scan(self, root: Path) -> list[Path]:
        try:
            st = root.stat()
        except OSError as exc:
            self._raise_fs_error(_classify_os_error(exc, root=True), root, str(exc))
        if not stat.S_ISDIR(st.st_mode):
            self._raise_fs_error(
                LibraryDiagnosticCode.DIRECTORY_MISSING, root, "not a directory"
            )
        files: list[Path] = []
        try:
            for entry in sorted(root.rglob("*")):
                if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
                    files.append(entry)
        except OSError as exc:
            self._raise_fs_error(_classify_traversal_error(exc), root, str(exc))
        return files

    def validate_file(self, path: Path) -> None:
        try:
            st = path.stat()
        except FileNotFoundError:
            self._raise_fs_error(LibraryDiagnosticCode.TRACK_MISSING, path)
        except OSError as exc:
            self._raise_fs_error(_classify_os_error(exc, root=False), path, str(exc))
        if not stat.S_ISREG(st.st_mode):
            self._raise_fs_error(LibraryDiagnosticCode.TRACK_MISSING, path)
