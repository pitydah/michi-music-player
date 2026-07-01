"""Playlist domain models — pure dataclasses, no Qt, no DB."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlaylistSummary:
    id: int = 0
    name: str = ""
    description: str = ""
    track_count: int = 0
    total_duration: float = 0.0
    cover_path: str = ""
    cover_type: str = "none"
    is_smart: bool = False
    is_locked: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0
    last_played: float = 0.0
    health_score: int = 100
    source: str = "local"
    sync_status: str = ""
    sync_version: int = 1


@dataclass
class PlaylistTrackRef:
    position: int = 0
    track_id: int = 0
    filepath: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    year: int = 0
    genre: str = ""
    duration: float = 0.0
    ext: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    quality_label: str = ""
    quality_kind: str = "unknown"
    track_uid: str = ""
    content_hash: str = ""
    musicbrainz_id: str = ""
    bpm: float = 0.0
    key: str = ""
    replaygain_track: float = 0.0
    replaygain_album: float = 0.0
    has_cover: bool = False
    missing_metadata: bool = False
    added_at: float = 0.0
    source: str = "manual"
    exists: bool = True


@dataclass
class PlaylistExportOptions:
    relative_paths: bool = False
    include_cover: bool = True
    include_lyrics: bool = False
    include_json: bool = True
    flat_structure: bool = True
    safe_mobile: bool = False
    overwrite: bool = False


@dataclass
class PlaylistImportPreview:
    total_entries: int = 0
    found: int = 0
    missing: int = 0
    remote: int = 0
    duplicates: int = 0
    already_indexed: int = 0
    not_indexed: int = 0
    entries: list[dict] = field(default_factory=list)


@dataclass
class PlaylistImportResult:
    ok: bool = False
    playlist_id: int = 0
    playlist_name: str = ""
    imported: int = 0
    skipped: int = 0
    message: str = ""


@dataclass
class PlaylistAuditIssue:
    issue_type: str = ""  # lost, duplicate, missing_metadata, missing_cover, empty, low_quality, remote
    severity: str = "info"  # info, warning, error
    message: str = ""
    track_id: int = 0
    filepath: str = ""
    details: dict | None = None


@dataclass
class PlaylistHealthReport:
    playlist_id: int = 0
    playlist_name: str = ""
    score: int = 100
    track_count: int = 0
    issues: list[PlaylistAuditIssue] = field(default_factory=list)
    stats: dict | None = None


@dataclass
class PlaylistRelinkCandidate:
    track_id: int = 0
    filepath: str = ""
    title: str = ""
    artist: str = ""
    score: int = 0
    match_type: str = ""  # uid, hash, filename, title_artist, duration, path


@dataclass
class PlaylistSmartRule:
    field: str = ""
    operator: str = "equals"
    value: str = ""


@dataclass
class PlaylistSmartDefinition:
    name: str = ""
    description: str = ""
    rules: list[PlaylistSmartRule] = field(default_factory=list)
    limit: int = 0
    sort_by: str = ""
    sort_direction: str = "asc"
    random: bool = False
    refresh_on_open: bool = True
    exclude_recently_played_days: int = 0
    avoid_same_artist: bool = False
    avoid_same_album: bool = False


@dataclass
class PlaylistSyncManifestEntry:
    id: str = ""
    name: str = ""
    description: str = ""
    updated_at: float = 0.0
    sync_version: int = 1
    is_smart: bool = False
    rules_hash: str = ""
    cover_id: str = ""
    track_count: int = 0
    duration: float = 0.0
    tracks_hash: str = ""


@dataclass
class PlaylistSyncManifest:
    format: str = "michi.playlists.manifest.v1"
    generated_at: float = 0.0
    device_id: str = ""
    playlists: list[PlaylistSyncManifestEntry] = field(default_factory=list)
    deleted_ids: list[int] = field(default_factory=list)
