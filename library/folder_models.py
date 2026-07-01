"""Folder models — pure dataclasses for folder browsing, health, and maintenance.

No Qt imports. Suitable for serialization, testing, and cross-layer use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FolderEntry:
    """A single filesystem entry inside a folder: file or subfolder."""

    path: str = ""
    name: str = ""
    kind: str = "unknown"  # folder, audio, unsupported_audio, cover, playlist, cue, log, text, unknown, error
    ext: str = ""
    size: int = 0
    mtime: float = 0.0
    is_hidden: bool = False
    is_supported_audio: bool = False
    is_indexed: bool = False
    db_id: int | None = None
    duration: float = 0.0
    title: str = ""
    artist: str = ""
    album: str = ""
    format_label: str = ""
    status: str = ""
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "kind": self.kind,
            "ext": self.ext,
            "size": self.size,
            "mtime": self.mtime,
            "is_hidden": self.is_hidden,
            "is_supported_audio": self.is_supported_audio,
            "is_indexed": self.is_indexed,
            "db_id": self.db_id,
            "duration": self.duration,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "format_label": self.format_label,
            "status": self.status,
            "problems": list(self.problems),
        }

    @classmethod
    def from_path(cls, path: str) -> "FolderEntry":
        name = os.path.basename(path) or path
        is_hidden = name.startswith(".")
        try:
            st = os.stat(path)
            size = st.st_size
            mtime = st.st_mtime
        except OSError:
            size = 0
            mtime = 0.0
        return cls(
            path=path,
            name=name,
            is_hidden=is_hidden,
            size=size,
            mtime=mtime,
        )


HEALTH_EXCELLENT = "excellent"
HEALTH_GOOD = "good"
HEALTH_ATTENTION = "attention"
HEALTH_WARNING = "warning"
HEALTH_CRITICAL = "critical"


@dataclass
class FolderHealth:
    """Health assessment of a single folder on disk."""

    path: str = ""
    exists: bool = False
    readable: bool = False
    is_library_root: bool = False
    is_inside_library_root: bool = False
    score: int = 0
    status: str = HEALTH_CRITICAL
    total_entries: int = 0
    subfolder_count: int = 0
    audio_count: int = 0
    indexed_audio_count: int = 0
    unindexed_audio_count: int = 0
    unsupported_audio_count: int = 0
    corrupted_count: int = 0
    missing_metadata_count: int = 0
    missing_cover: bool = False
    mixed_formats: bool = False
    formats: list[str] = field(default_factory=list)
    missing_db_paths_count: int = 0
    permission_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "readable": self.readable,
            "is_library_root": self.is_library_root,
            "is_inside_library_root": self.is_inside_library_root,
            "score": self.score,
            "status": self.status,
            "total_entries": self.total_entries,
            "subfolder_count": self.subfolder_count,
            "audio_count": self.audio_count,
            "indexed_audio_count": self.indexed_audio_count,
            "unindexed_audio_count": self.unindexed_audio_count,
            "unsupported_audio_count": self.unsupported_audio_count,
            "corrupted_count": self.corrupted_count,
            "missing_metadata_count": self.missing_metadata_count,
            "missing_cover": self.missing_cover,
            "mixed_formats": self.mixed_formats,
            "formats": list(self.formats),
            "missing_db_paths_count": self.missing_db_paths_count,
            "permission_errors": list(self.permission_errors),
            "warnings": list(self.warnings),
            "recommended_actions": list(self.recommended_actions),
        }


@dataclass
class FolderProblem:
    """A specific problem found in a folder or file."""

    path: str = ""
    problem_type: str = ""  # missing_metadata, missing_cover, unsupported, corrupted, permission, missing_from_db, mixed_formats, not_indexed, outside_library
    severity: str = "info"  # info, warning, critical
    description: str = ""
    suggested_action: str = ""
    action_label: str = ""
    file_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FolderIntegrityResult:
    """Integrity verification result for a folder or file set."""

    path: str = ""
    deep: bool = False
    total_files: int = 0
    checked_files: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    corrupted_files: list[str] = field(default_factory=list)
    skipped_files: int = 0
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return not self.errors and not self.corrupted_files


@dataclass
class FolderDbDiff:
    """Differences between filesystem and database for a folder."""

    path: str = ""
    in_fs_not_db: list[str] = field(default_factory=list)
    in_db_not_fs: list[str] = field(default_factory=list)
    size_mismatch: list[tuple[str, int, int]] = field(default_factory=list)
    mtime_mismatch: list[tuple[str, float, float]] = field(default_factory=list)
    fs_audio_count: int = 0
    db_audio_count: int = 0

    @property
    def has_differences(self) -> bool:
        return bool(self.in_fs_not_db or self.in_db_not_fs or self.size_mismatch or self.mtime_mismatch)


@dataclass
class FolderActionRecommendation:
    """A recommended action for a folder health issue."""

    action: str = ""       # scan_folder, add_library_root, open_metadata_editor, find_cover, review_formats, cleanup_missing, convert_or_ignore, open_in_file_manager
    label: str = ""        # Spanish label for UI button
    severity: str = "info"
    priority: int = 0      # higher = more important
    description: str = ""
    affected_count: int = 0
    requires_confirmation: bool = False


@dataclass
class FolderMovePlan:
    """Pre-flight plan for moving/renaming a folder."""

    source: str = ""
    destination: str = ""
    is_rename: bool = False
    files_to_move: int = 0
    folders_to_move: int = 0
    total_size_bytes: int = 0
    affected_media_items: int = 0
    affected_playlists: list[str] = field(default_factory=list)
    affected_favorites: int = 0
    affected_history: int = 0
    affected_sidecar_covers: list[str] = field(default_factory=list)
    affected_cue_files: list[str] = field(default_factory=list)
    affected_playlist_files: list[str] = field(default_factory=list)
    same_filesystem: bool = False
    destination_outside_root: bool = False
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    can_proceed: bool = False


@dataclass
class FolderMoveResult:
    """Result of a completed move/rename operation."""

    success: bool = False
    source: str = ""
    destination: str = ""
    files_moved: int = 0
    files_failed: list[str] = field(default_factory=list)
    db_updated: int = 0
    db_failed: list[str] = field(default_factory=list)
    playlists_updated: int = 0
    rollback_performed: bool = False
    rollback_success: bool = False
    error_message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def classify_status(score: int) -> str:
    if score >= 90:
        return HEALTH_EXCELLENT
    if score >= 75:
        return HEALTH_GOOD
    if score >= 55:
        return HEALTH_ATTENTION
    if score >= 30:
        return HEALTH_WARNING
    return HEALTH_CRITICAL
