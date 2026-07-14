from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from core.metadata.enums import (
    FieldOperation, MatchClassification, JournalStatus,
)


@dataclass
class TrackIdentity:
    library_track_id: str = ""
    filepath: str = ""
    content_hash: str = ""
    audio_fingerprint: str = ""
    isrc: str = ""
    musicbrainz_recording_id: str = ""
    title: str = ""
    artists: list[str] = field(default_factory=list)
    album: str = ""
    album_artist: str = ""
    duration_ms: int = 0
    track_number: int = 0
    disc_number: int = 0


@dataclass
class TrackMetadata:
    title: str = ""
    artists: list[str] = field(default_factory=list)
    album: str = ""
    album_artist: str = ""
    track_number: int | None = None
    track_total: int | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    date: str = ""
    original_date: str = ""
    release_year: int | None = None
    genres: list[str] = field(default_factory=list)
    composer: str = ""
    performers: list[str] = field(default_factory=list)
    conductor: str = ""
    lyricist: str = ""
    comment: str = ""
    copyright_: str = ""
    publisher: str = ""
    label: str = ""
    bpm: float | None = None
    key: str = ""
    language: str = ""
    compilation: bool | None = None
    isrc: str = ""
    barcode: str = ""
    catalog_number: str = ""
    musicbrainz_recording_id: str = ""
    musicbrainz_release_id: str = ""
    musicbrainz_release_group_id: str = ""
    musicbrainz_artist_ids: list[str] = field(default_factory=list)
    musicbrainz_album_artist_ids: list[str] = field(default_factory=list)
    acoustid_id: str = ""
    replaygain_track_gain: float | None = None
    replaygain_track_peak: float | None = None
    replaygain_album_gain: float | None = None
    replaygain_album_peak: float | None = None
    r128_track_gain: float | None = None
    r128_album_gain: float | None = None
    lyrics: str = ""
    custom_fields: dict[str, str] = field(default_factory=dict)


@dataclass
class TechnicalMetadata:
    container: str = ""
    codec: str = ""
    codec_profile: str = ""
    duration_ms: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    channel_layout: str = ""
    lossless: bool = False
    filesize: int = 0
    mtime_ns: int = 0
    audio_stream_count: int = 0


@dataclass
class ArtworkMetadata:
    artwork_id: str = ""
    picture_type: str = "front_cover"
    mime_type: str = ""
    width: int = 0
    height: int = 0
    depth: int = 8
    size_bytes: int = 0
    description: str = ""
    content_hash: str = ""
    data_reference: str = ""


@dataclass
class MetadataDocument:
    source_path: str = ""
    format: str = ""
    track: TrackMetadata = field(default_factory=TrackMetadata)
    technical: TechnicalMetadata = field(default_factory=TechnicalMetadata)
    artworks: list[ArtworkMetadata] = field(default_factory=list)
    raw_fields: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    read_at: str = ""
    file_signature: str = ""


@dataclass
class MetadataFieldChange:
    field: str = ""
    old_value: Any = None
    new_value: Any = None
    operation: FieldOperation = FieldOperation.SET
    confidence: float = 1.0
    source: str = ""
    reason: str = ""
    selected: bool = True


@dataclass
class MetadataPatch:
    patch_id: str = ""
    target: str = ""
    changes: list[MetadataFieldChange] = field(default_factory=list)
    artwork_changes: list[MetadataFieldChange] = field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    reason: str = ""
    created_at: str = ""


@dataclass
class MetadataOperationResult:
    ok: bool = True
    code: str = "ok"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    retryable: bool = False
    cancelled: bool = False
    partial: bool = False
    correlation_id: str = ""
    trace_id: str = ""


T = TypeVar("T")


@dataclass
class TypedMetadataResult(Generic[T]):
    ok: bool = True
    code: str = "ok"
    message: str = ""
    data: T | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    retryable: bool = False
    cancelled: bool = False


@dataclass
class MatcherCandidate:
    candidate: MetadataDocument | None = None
    score: float = 0.0
    classification: MatchClassification = MatchClassification.NO_MATCH
    field_scores: dict[str, float] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reasoning_summary: str = ""


@dataclass
class MetadataProposal:
    proposal_id: str = ""
    target: str = ""
    current_metadata: MetadataDocument = field(default_factory=MetadataDocument)
    candidate: MetadataDocument | None = None
    field_changes: list[MetadataFieldChange] = field(default_factory=list)
    artwork_changes: list[MetadataFieldChange] = field(default_factory=list)
    confidence: float = 0.0
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source: str = ""
    created_at: str = ""


@dataclass
class BackupEntry:
    operation_id: str = ""
    target: str = ""
    before_signature: str = ""
    backup_path: str = ""
    backup_type: str = ""
    created_at: str = ""
    size_bytes: int = 0


@dataclass
class JournalEntry:
    operation_id: str = ""
    batch_id: str = ""
    target: str = ""
    status: JournalStatus = JournalStatus.PLANNED
    before_signature: str = ""
    after_signature: str = ""
    patch: str = ""
    backup_reference: str = ""
    started_at: str = ""
    completed_at: str = ""
    result_code: str = ""
    rollback_status: str = ""


@dataclass
class BatchSession:
    batch_id: str = ""
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    cancelled: bool = False
    current_item: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class DuplicateGroup:
    level: str = ""
    tracks: list[TrackIdentity] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class FormatCapability:
    format_id: str = ""
    extensions: list[str] = field(default_factory=list)
    mime_types: list[str] = field(default_factory=list)
    readable: bool = False
    writable: bool = False
    artwork_readable: bool = False
    artwork_writable: bool = False
    lyrics_readable: bool = False
    lyrics_writable: bool = False
    multi_value_support: bool = False
    custom_field_support: bool = False
    lossless_write: bool = False
    requirements: list[str] = field(default_factory=list)


@dataclass
class MetadataExportProfile:
    profile_id: str = ""
    include_fields: list[str] = field(default_factory=list)
    simplify_fields: dict[str, str] = field(default_factory=dict)
    max_artwork_bytes: int = 0
    lossy_text: bool = False


def compute_file_signature(filepath: str) -> str:
    try:
        import os
        st = os.stat(filepath)
        raw = f"{st.st_size}:{st.st_mtime_ns}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except (OSError, IOError):
        return ""
