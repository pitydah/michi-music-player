from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum


class LyricsSource(Enum):
    EMBEDDED = "embedded"
    SIDECAR_LRC = "sidecar_lrc"
    SIDECAR_TEXT = "sidecar_text"
    CACHE = "cache"
    REMOTE_PROVIDER = "remote_provider"
    MANUAL = "manual"


class LyricsStatus(Enum):
    IDLE = "idle"
    RESOLVING = "resolving"
    FOUND = "found"
    NOT_FOUND = "not_found"
    OFFLINE = "offline"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class MatchConfidence(Enum):
    EXACT = "exact"
    HIGH_CONFIDENCE = "high_confidence"
    AMBIGUOUS = "ambiguous"
    LOW_CONFIDENCE = "low_confidence"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class LyricsErrorCode(Enum):
    OK = "ok"
    INVALID_IDENTITY = "invalid_identity"
    NO_SEARCHABLE_METADATA = "no_searchable_metadata"
    NOT_FOUND = "not_found"
    AMBIGUOUS_MATCH = "ambiguous_match"
    OFFLINE = "offline"
    PROVIDER_DISABLED = "provider_disabled"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_INVALID_RESPONSE = "provider_invalid_response"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    INVALID_LRC = "invalid_lrc"
    CACHE_ERROR = "cache_error"
    READ_ERROR = "read_error"
    WRITE_ERROR = "write_error"
    PATH_REJECTED = "path_rejected"
    CANCELLED = "cancelled"
    STALE_RESULT = "stale_result"
    ATTRIBUTION_REQUIRED = "attribution_required"
    UNSUPPORTED_FORMAT = "unsupported_format"
    INTERNAL_ERROR = "internal_error"


@dataclass
class TrackIdentity:
    track_id: str = ""
    filepath: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    duration_ms: int = 0
    disc_number: int = 0
    track_number: int = 0
    musicbrainz_track_id: str = ""
    isrc: str = ""


@dataclass
class LyricsWord:
    start_ms: float = 0.0
    end_ms: float = 0.0
    text: str = ""


@dataclass
class LyricsLine:
    line_id: str = ""
    start_ms: float = 0.0
    end_ms: float = 0.0
    text: str = ""
    translation: str = ""
    speaker: str = ""
    words: list[LyricsWord] = field(default_factory=list)


@dataclass
class LyricsMetadata:
    artist: str = ""
    album: str = ""
    title: str = ""
    author: str = ""
    editor: str = ""
    version: str = ""
    language: str = ""
    offset_ms: int = 0


@dataclass
class LyricsAttribution:
    source_label: str = ""
    provider_url: str = ""
    provider_id: str = ""
    license_hint: str = ""
    terms_reference: str = ""


@dataclass
class LyricsDocument:
    document_id: str = ""
    identity: TrackIdentity = field(default_factory=TrackIdentity)
    plain_text: str = ""
    synced_text: str = ""
    lines: list[LyricsLine] = field(default_factory=list)
    metadata: LyricsMetadata = field(default_factory=LyricsMetadata)
    source: LyricsSource = LyricsSource.MANUAL
    provider_id: str = ""
    provider_item_id: str = ""
    language: str = ""
    instrumental: bool = False
    verified: bool = False
    match_confidence: MatchConfidence = MatchConfidence.UNKNOWN
    duration_ms: int = 0
    offset_ms: int = 0
    attribution: LyricsAttribution = field(default_factory=LyricsAttribution)
    fetched_at: str = ""
    updated_at: str = ""
    content_hash: str = ""

    @property
    def has_synced(self) -> bool:
        return bool(self.synced_text) or any(
            ln.start_ms > 0 or ln.end_ms > 0 for ln in self.lines
        )

    @property
    def has_plain(self) -> bool:
        return bool(self.plain_text) or any(
            ln.text.strip() for ln in self.lines
        )


@dataclass
class LyricsOperationResult:
    ok: bool = True
    code: LyricsErrorCode = LyricsErrorCode.OK
    message: str = ""
    document: LyricsDocument | None = None
    candidates: list[LyricsDocument] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retryable: bool = False
    cancelled: bool = False
    source: LyricsSource = LyricsSource.MANUAL
    trace_id: str = ""


@dataclass
class ProviderContract:
    provider_id: str
    display_name: str
    enabled: bool = True
    priority: int = 100
    supports_exact: bool = True
    supports_search: bool = True
    supports_synced: bool = True
    supports_plain: bool = True
    supports_instrumental: bool = False
    requires_network: bool = True
    rate_limit_rps: float = 0.0
    attribution: LyricsAttribution = field(default_factory=LyricsAttribution)
    cache_policy: str = "positive_and_negative"
    timeout_ms: int = 10000


@dataclass
class LyricsSettings:
    enabled: bool = True
    provider_order: list[str] = field(default_factory=lambda: ["lrclib"])
    remote_enabled: bool = True
    offline_mode: bool = False
    prefer_synced: bool = True
    allow_plain: bool = True
    preferred_language: str = ""
    request_timeout_ms: int = 10000
    negative_cache_ttl_s: int = 3600
    positive_cache_ttl_s: int = 86400
    cache_size_mb: int = 50
    auto_search_current_track: bool = True
    save_remote_to_cache: bool = True
    sidecar_write_policy: str = "atomic"
    embedded_write_policy: str = "never"
    cache_db_path: str = ""


@dataclass
class NormalizedIdentity:
    original: TrackIdentity = field(default_factory=TrackIdentity)
    normalized_title: str = ""
    normalized_artist: str = ""
    normalized_album: str = ""
    matching_tokens: list[str] = field(default_factory=list)


def compute_track_hash(identity: TrackIdentity) -> str:
    raw = "||".join([
        identity.title.lower().strip(),
        identity.artist.lower().strip(),
        identity.album.lower().strip(),
        str(identity.duration_ms),
        identity.musicbrainz_track_id,
        identity.isrc,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]
