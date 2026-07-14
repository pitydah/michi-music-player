from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


StationId = int


class ProbeStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class SessionState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    BUFFERING = "buffering"
    PLAYING = "playing"
    RECONNECTING = "reconnecting"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RadioError(Enum):
    NONE = ""
    URL_INVALID = "url_invalid"
    URL_UNSUPPORTED_SCHEME = "url_unsupported_scheme"
    URL_MALFORMED = "url_malformed"
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    TLS_ERROR = "tls_error"
    UNSUPPORTED_CONTENT_TYPE = "unsupported_content_type"
    STREAM_NOT_FOUND = "stream_not_found"
    SERVER_ERROR = "server_error"
    REDIRECT_LIMIT = "redirect_limit"
    CANCELLED = "cancelled"
    DATABASE_ERROR = "database_error"
    NOT_FOUND = "not_found"
    EXPORT_FAILED = "export_failed"
    IMPORT_FAILED = "import_failed"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class Station:
    id: StationId
    name: str
    stream_url: str
    homepage_url: str = ""
    favicon_url: str = ""
    genre: str = ""
    country: str = ""
    language: str = ""
    codec: str = ""
    bitrate: int = 0
    favorite: bool = False
    created_at: str = ""
    updated_at: str = ""
    last_played_at: str = ""
    play_count: int = 0
    last_probe_status: str = ""
    last_probe_at: str = ""


@dataclass
class StationCreateRequest:
    name: str
    stream_url: str
    homepage_url: str = ""
    favicon_url: str = ""
    genre: str = ""
    country: str = ""
    language: str = ""
    codec: str = ""
    bitrate: int = 0


@dataclass
class StationUpdateRequest:
    name: str | None = None
    stream_url: str | None = None
    homepage_url: str | None = None
    favicon_url: str | None = None
    genre: str | None = None
    country: str | None = None
    language: str | None = None
    codec: str | None = None
    bitrate: int | None = None
    favorite: bool | None = None


@dataclass
class StreamCapabilities:
    supports_icy: bool = False
    supports_playlist: bool = False
    codec: str = ""
    bitrate: int = 0


@dataclass
class StreamMetadata:
    icy_name: str = ""
    icy_genre: str = ""
    icy_url: str = ""
    icy_br: str = ""
    icy_description: str = ""
    stream_title: str = ""
    stream_url: str = ""


@dataclass
class StreamProbeResult:
    requested_url: str
    final_url: str = ""
    status: ProbeStatus = ProbeStatus.ERROR
    http_status: int = 0
    content_type: str = ""
    codec: str = ""
    bitrate: int = 0
    icy_name: str = ""
    icy_genre: str = ""
    icy_url: str = ""
    icy_metaint: int = 0
    redirect_count: int = 0
    latency_ms: float = 0.0
    supports_metadata: bool = False
    error: str = ""
    capabilities: StreamCapabilities = field(default_factory=StreamCapabilities)
    metadata: StreamMetadata = field(default_factory=StreamMetadata)


@dataclass
class StreamSessionState:
    station_id: StationId
    state: SessionState = SessionState.IDLE
    stream_url: str = ""
    metadata: StreamMetadata = field(default_factory=StreamMetadata)
    error: RadioError = RadioError.NONE
    error_message: str = ""
    reconnect_attempt: int = 0
    started_at: str = ""
    generation: int = 0


@dataclass
class ReconnectPolicyConfig:
    enabled: bool = True
    max_attempts: int = 10
    max_total_seconds: int = 300
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    jitter_ms: int = 500


class AtomicMode(Enum):
    ALL_OR_NOTHING = "all_or_nothing"
    BEST_EFFORT = "best_effort"


@dataclass
class ImportResult:
    total_entries: int = 0
    imported: int = 0
    updated: int = 0
    duplicates: int = 0
    invalid: int = 0
    failed: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ExportResult:
    path: str = ""
    count: int = 0
    ok: bool = False
    error: str = ""


@dataclass
class RadioOperationResult:
    ok: bool = True
    code: str = ""
    message: str = ""
    station: Station | None = None
    stations: list[Station] = field(default_factory=list)
    error: RadioError = RadioError.NONE
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaginatedResult:
    items: list[Station] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 1
