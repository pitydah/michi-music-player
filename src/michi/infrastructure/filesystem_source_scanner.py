"""Source-aware filesystem scanner (M6-EXT-R4-K).

Discovers FILESYSTEM FACTS inside ONE LibrarySource root: absolute path,
validated relative path, size/mtime fingerprint, and (best-effort)
device/inode as a same-filesystem relocation hint. Never allocates
TrackIds, never mutates the catalog.

Symlink policy (contract): directory symlinks are NOT recursively followed —
cycles, duplicate traversal and source escapes are forbidden; a symlinked
directory inside a source is enumerated as a non-directory (skipped) entry
candidate, never traversed.
"""

import logging
import stat as stat_module
from pathlib import Path

from michi.application.library_port import (
    DiscoveredMediaFile,
    LibraryFilesystemError,
    LibrarySourceScannerPort,
)
from michi.domain.library import LibraryDiagnosticCode
from michi.domain.library_catalog import LibrarySource, validate_relative_media_path

logger = logging.getLogger(__name__)

_MEDIA_SUFFIXES = {
    ".mp3",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".m4a",
    ".mp4",
    ".aac",
    ".wav",
    ".wv",
    ".ape",
    ".dsf",
    ".dff",
    ".aiff",
    ".aif",
    ".alac",
}


class FilesystemLibrarySourceScanner(LibrarySourceScannerPort):
    """Walks one source root deterministically (sorted) without following
    directory symlinks."""

    def discover(self, source: LibrarySource) -> tuple[DiscoveredMediaFile, ...]:
        root = Path(source.root_path)
        try:
            stat = root.stat()
        except FileNotFoundError as exc:
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.DIRECTORY_MISSING, root, str(exc)
            ) from exc
        except PermissionError as exc:
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.ACCESS_FAILURE, root, str(exc)
            ) from exc
        except OSError as exc:
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.IO_FAILURE, root, str(exc)
            ) from exc
        if not stat_module.S_ISDIR(stat.st_mode):
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.UNKNOWN_FAILURE,
                root,
                "source root is not a directory",
            )

        discovered: list[DiscoveredMediaFile] = []
        for path in self._walk(root):
            if path.suffix.lower() not in _MEDIA_SUFFIXES:
                continue
            try:
                relative = validate_relative_media_path(
                    path.relative_to(root).as_posix()
                )
            except ValueError:
                continue  # cannot escape: relative_to already guarantees it
            try:
                info = path.stat()
                device_id = getattr(info, "st_dev", 0)
                inode = getattr(info, "st_ino", 0)
            except OSError:
                continue  # vanished mid-walk: skip honestly
            discovered.append(
                DiscoveredMediaFile(
                    absolute_path=path,
                    relative_path=relative,
                    file_size=info.st_size,
                    mtime_ns=int(info.st_mtime_ns),
                    device_id=int(device_id),
                    inode=int(inode),
                )
            )
        return tuple(discovered)

    def _walk(self, root: Path):
        """Deterministic bounded walk: sorted entries, directory symlinks
        skipped (never followed), OSError on a subdirectory logged + skipped."""
        stack = [root]
        while stack:
            directory = stack.pop()
            try:
                entries = sorted(directory.iterdir(), key=lambda p: p.name)
            except OSError as exc:
                logger.warning(
                    "source walk skipped unreadable directory %s: %s", directory, exc
                )
                continue
            for entry in entries:
                try:
                    is_dir = entry.is_dir()  # follows symlinks for the CHECK
                except OSError:
                    continue
                if is_dir:
                    if entry.is_symlink():
                        # Contract: never follow directory symlinks.
                        continue
                    stack.append(entry)
                    continue
                yield entry

    def validate_file(self, path: Path) -> None:
        """TD-013 shared gate: raise LibraryFilesystemError when the file is
        not a playable regular file."""
        try:
            if not path.is_file():
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.TRACK_MISSING, path, "file does not exist"
                )
        except OSError as exc:
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.IO_FAILURE, path, str(exc)
            ) from exc
