"""One-way, verified migration of legacy Ecosystem state into the Player root.

The incubator historically stored Home and account state below
``$XDG_DATA_HOME/michi``.  The Player uses its own Qt application-data root.
This module migrates those directories exactly once, preserves the legacy copy
for rollback, and fails closed on any ambiguity.  It never deletes or rewrites
the legacy data and never merges two state trees.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_READ_CHUNK = 1024 * 1024


class StorageMigrationError(RuntimeError):
    """Legacy storage cannot be migrated without risking the Home identity."""


@dataclass(frozen=True)
class MigrationResult:
    state: str
    source: str | None
    target: str | None
    backup: str | None
    file_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "source": self.source,
            "target": self.target,
            "backup": self.backup,
            "file_count": self.file_count,
        }


def _files(root: Path) -> list[Path]:
    """Return regular files in deterministic order; reject links/specials."""
    result: list[Path] = []
    for current, directories, names in os.walk(root, followlinks=False):
        base = Path(current)
        for name in sorted(directories):
            candidate = base / name
            if candidate.is_symlink():
                raise StorageMigrationError(f"symlink in legacy state: {candidate}")
        directories.sort()
        for name in sorted(names):
            candidate = base / name
            if candidate.is_symlink():
                raise StorageMigrationError(f"symlink in legacy state: {candidate}")
            if not candidate.is_file():
                raise StorageMigrationError(
                    f"non-regular file in legacy state: {candidate}"
                )
            result.append(candidate)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_READ_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_tree(root: Path, files: list[Path]) -> None:
    for path in files:
        with contextlib.suppress(OSError):
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    with contextlib.suppress(OSError):
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _copy_verified(source: Path, target: Path) -> list[Path]:
    """Copy source into a new target and verify every file byte-for-byte."""
    if target.exists():
        raise StorageMigrationError(f"migration target already exists: {target}")
    source_files = _files(source)
    if not source_files:
        raise StorageMigrationError(f"legacy state is empty: {source}")
    shutil.copytree(source, target, symlinks=False)
    target_files = _files(target)
    if len(target_files) != len(source_files):
        raise StorageMigrationError("migration changed the file inventory")
    for original in source_files:
        relative = original.relative_to(source)
        copy = target / relative
        if _sha256(original) != _sha256(copy):
            raise StorageMigrationError(f"migration hash mismatch: {relative}")
    _fsync_tree(target, target_files)
    return target_files


def migrate_state(
    *,
    source: Path | None,
    target: Path,
    backup_root: Path,
    environ: Mapping[str, str] | None = None,
) -> MigrationResult:
    """Migrate one legacy state directory without merging or overwriting.

    ``source is None`` or a missing/empty source is a no-op.  If the target
    already contains anything, migration is refused and nothing is touched.
    """
    del environ  # retained for an explicit, future environment-aware policy
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        return MigrationResult("target_present", None, str(target), None, 0)

    if source is None:
        return MigrationResult("no_legacy", None, str(target), None, 0)
    source = Path(source)
    if not source.exists() or not source.is_dir():
        return MigrationResult("no_legacy", None, str(target), None, 0)
    if not any(source.iterdir()):
        return MigrationResult("no_legacy", str(source), str(target), None, 0)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = Path(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        backup_root.chmod(0o700)
    backup = backup_root / stamp
    backup_files = _copy_verified(source, backup)

    temporary = target.with_name(target.name + ".migrating")
    if temporary.exists():
        raise StorageMigrationError(f"stale migration temporary: {temporary}")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    copied_files: list[Path] = []
    try:
        copied_files = _copy_verified(source, temporary)
        if target.exists():
            if any(target.iterdir()):
                raise StorageMigrationError("target became non-empty during migration")
            target.rmdir()
        os.replace(temporary, target)
        with contextlib.suppress(OSError):
            descriptor = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except Exception:
        with contextlib.suppress(OSError):
            if temporary.exists():
                shutil.rmtree(temporary)
        raise

    if len(copied_files) != len(backup_files):
        raise StorageMigrationError("migration backup and target differ")
    return MigrationResult(
        "migrated",
        str(source),
        str(target),
        str(backup),
        len(copied_files),
    )
