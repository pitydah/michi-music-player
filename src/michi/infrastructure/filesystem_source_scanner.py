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
    SUPPORTED_MEDIA_SUFFIXES,
    DiscoveredMediaFile,
    LibraryFilesystemError,
    LibrarySourceScannerPort,
)
from michi.domain.library import LibraryDiagnosticCode
from michi.domain.library_catalog import LibrarySource, validate_relative_media_path

logger = logging.getLogger(__name__)

# M6-EXT-R4 freeze gate §23: ONE supported-media policy (the pre-R4
# contract set). R4 is resilience, not a format expansion program.
_MEDIA_SUFFIXES = SUPPORTED_MEDIA_SUFFIXES


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

        return self._collect_discovered(root, None, None)

    def _collect_discovered(
        self, root, token, on_entry
    ) -> tuple[DiscoveredMediaFile, ...]:
        discovered: list[DiscoveredMediaFile] = []
        for path in self._walk(root):
            if token is not None and token.cancelled:
                from michi.application.ports import ScanCancelled

                raise ScanCancelled()
            if on_entry is not None:
                on_entry(path)
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
        skipped (never followed).

        P1-LIB-07 FAIL-CLOSED enumeration: an unreadable nested directory
        ABORTS the whole source observation (typed LibraryFilesystemError)
        instead of silently skipping it. A skipped subtree would make the
        coordinator fabricate authoritative MISSING records for its known
        children — false physical truth. FileNotFoundError is the ONLY
        honest skip (a path vanished mid-walk)."""
        stack = [root]
        while stack:
            directory = stack.pop()
            try:
                entries = sorted(directory.iterdir(), key=lambda p: p.name)
            except FileNotFoundError:
                continue  # a path vanished during the walk: honest skip
            except PermissionError as exc:
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.ACCESS_FAILURE, directory, str(exc)
                ) from exc
            except OSError as exc:
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.IO_FAILURE, directory, str(exc)
                ) from exc
            for entry in entries:
                try:
                    is_dir = entry.is_dir()  # follows symlinks for the CHECK
                except FileNotFoundError:
                    continue  # vanished mid-walk
                except PermissionError as exc:
                    raise LibraryFilesystemError(
                        LibraryDiagnosticCode.ACCESS_FAILURE, entry, str(exc)
                    ) from exc
                except OSError as exc:
                    raise LibraryFilesystemError(
                        LibraryDiagnosticCode.IO_FAILURE, entry, str(exc)
                    ) from exc
                if is_dir:
                    if entry.is_symlink():
                        # Contract: never follow directory symlinks.
                        continue
                    stack.append(entry)
                    continue
                yield entry

    def discover_cancellable(
        self,
        source: LibrarySource,
        token=None,
        on_entry=None,
    ) -> tuple[DiscoveredMediaFile, ...]:
        """P1/CONCURRENCY-LIB-03A: the productive async walk is
        cooperatively cancellable — between directory/entry operations the
        token is checked so Cancel during a huge tree walk stops promptly.

        A subclass that overrides ``discover`` (frozen legacy fakes raise
        typed errors there) keeps its override authoritative: the override
        is respected without cancellation rather than bypassed."""
        if type(self).discover is not FilesystemLibrarySourceScanner.discover:
            return self.discover(source)
        return self._collect_discovered(Path(source.root_path), token, on_entry)

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
