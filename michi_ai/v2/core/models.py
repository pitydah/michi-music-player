from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ErrorCode(str, Enum):
    OK = "OK"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS_INTENT = "AMBIGUOUS_INTENT"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_CANCELLED = "TOOL_CANCELLED"
    TOOL_FAILED = "TOOL_FAILED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_EXPIRED = "CONFIRMATION_EXPIRED"
    PLAN_INVALID = "PLAN_INVALID"
    PLAN_STEP_FAILED = "PLAN_STEP_FAILED"
    PLAN_CANCELLED = "PLAN_CANCELLED"
    ROLLBACK_SUCCEEDED = "ROLLBACK_SUCCEEDED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    CONTEXT_REJECTED = "CONTEXT_REJECTED"
    PRIVACY_BLOCKED = "PRIVACY_BLOCKED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class OperationResult(Generic[T]):
    ok: bool
    code: ErrorCode = ErrorCode.OK
    message: str = ""
    data: T | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    requires_confirmation: bool = False
    retryable: bool = False
    cancelled: bool = False
    correlation_id: str = ""

    @staticmethod
    def success(data: T | None = None, message: str = "", warnings: tuple[str, ...] = ()) -> OperationResult[T]:
        return OperationResult(
            ok=True, code=ErrorCode.OK, message=message,
            data=data, warnings=warnings,
            correlation_id=uuid.uuid4().hex[:12],
        )

    @staticmethod
    def failure(
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: str = "",
        errors: tuple[str, ...] = (),
        retryable: bool = False,
    ) -> OperationResult[T]:
        return OperationResult(
            ok=False, code=code, message=message,
            errors=errors, retryable=retryable,
            correlation_id=uuid.uuid4().hex[:12],
        )

    @staticmethod
    def confirmation(message: str, correlation_id: str = "") -> OperationResult[T]:
        return OperationResult(
            ok=False, code=ErrorCode.CONFIRMATION_REQUIRED,
            message=message, requires_confirmation=True,
            correlation_id=correlation_id or uuid.uuid4().hex[:12],
        )

    def with_data(self, data: T) -> OperationResult[T]:
        return OperationResult(
            ok=self.ok, code=self.code, message=self.message,
            data=data, warnings=self.warnings, errors=self.errors,
            requires_confirmation=self.requires_confirmation,
            retryable=self.retryable, cancelled=self.cancelled,
            correlation_id=self.correlation_id,
        )

    def with_warning(self, warning: str) -> OperationResult[T]:
        return OperationResult(
            ok=self.ok, code=self.code, message=self.message,
            data=self.data, warnings=self.warnings + (warning,),
            errors=self.errors, requires_confirmation=self.requires_confirmation,
            retryable=self.retryable, cancelled=self.cancelled,
            correlation_id=self.correlation_id,
        )


class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    PLAYBACK_CONTROL = "PLAYBACK_CONTROL"
    LIBRARY_MUTATION = "LIBRARY_MUTATION"
    SETTINGS_MUTATION = "SETTINGS_MUTATION"
    DEVICE_TRANSFER = "DEVICE_TRANSFER"
    NETWORK_CONFIGURATION = "NETWORK_CONFIGURATION"
    DESTRUCTIVE = "DESTRUCTIVE"


class ConfirmationMode(str, Enum):
    NONE = "NONE"
    SOFT = "SOFT"
    EXPLICIT = "EXPLICIT"
    DESTRUCTIVE = "DESTRUCTIVE"
    IRREVERSIBLE = "IRREVERSIBLE"


class PrivacyLevel(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    DIAGNOSTIC = "DIAGNOSTIC"
    LOCAL_FULL = "LOCAL_FULL"


class AssistantResponseType(str, Enum):
    ANSWER = "ANSWER"
    CLARIFICATION = "CLARIFICATION"
    PLAN_PREVIEW = "PLAN_PREVIEW"
    CONFIRMATION_REQUEST = "CONFIRMATION_REQUEST"
    EXECUTION_PROGRESS = "EXECUTION_PROGRESS"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    ERROR = "ERROR"
    SUGGESTION = "SUGGESTION"


@dataclass(frozen=True)
class AssistantRequest:
    text: str
    session_id: str = ""
    context_snapshot_id: str = ""
    allowed_capabilities: tuple[str, ...] = ()
    correlation_id: str = ""


@dataclass(frozen=True)
class AssistantResponse:
    type: AssistantResponseType
    title: str = ""
    message: str = ""
    details: str = ""
    actions: tuple[dict[str, Any], ...] = ()
    plan: Any | None = None
    progress: dict[str, Any] | None = None
    error: str = ""
    trace_id: str = ""
    correlation_id: str = ""


@dataclass
class AssistantSession:
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active_context: dict[str, Any] = field(default_factory=dict)
    turns: list[ConversationTurn] = field(default_factory=list)
    pending_plan: Any | None = None
    pending_confirmation: Any | None = None
    last_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextSnapshot:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str = ""
    active_section: str = ""
    active_entity: dict[str, Any] = field(default_factory=dict)
    selection: dict[str, Any] = field(default_factory=dict)
    playback: dict[str, Any] = field(default_factory=dict)
    queue: dict[str, Any] = field(default_factory=dict)
    library: dict[str, Any] = field(default_factory=dict)
    devices: dict[str, Any] = field(default_factory=dict)
    servers: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    jobs: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    recent_actions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    _privacy_level: PrivacyLevel = PrivacyLevel.STANDARD


@dataclass(frozen=True)
class SanitizedContext:
    snapshot: ContextSnapshot
    sanitized_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    removed_fields: tuple[str, ...] = ()
    truncated_fields: tuple[str, ...] = ()
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD


@dataclass(frozen=True)
class ParsedIntent:
    intent_id: str
    confidence: float
    source: str
    entities: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    requested_actions: tuple[str, ...] = ()
    negated_actions: tuple[str, ...] = ()
    requires_clarification: bool = False
    clarification_question: str = ""
    requires_confirmation: bool = False
    reasoning_summary: str = ""
    matched_rule: str = ""


@dataclass(frozen=True)
class IntentCandidate:
    intent: ParsedIntent
    rank: int = 0


@dataclass(frozen=True)
class ExtractedEntity:
    name: str
    value: Any
    confidence: float = 1.0
    source_text: str = ""
    resolved: bool = True
    resolution_scope: str = ""


@dataclass(frozen=True)
class Ambiguity:
    field: str
    candidates: tuple[Any, ...] = ()
    clarification_question: str = ""
    resolved: bool = False


@dataclass(frozen=True)
class Capability:
    name: str
    available: bool = True
    degraded: bool = False
    reason: str = ""
    requires_confirmation: bool = False
    permission: PermissionLevel = PermissionLevel.READ_ONLY


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    version: str = "1.0.0"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    permission: PermissionLevel = PermissionLevel.READ_ONLY
    capabilities: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    requires_confirmation: bool = False
    confirmation_policy: str = "NONE"
    destructive: bool = False
    idempotent: bool = True
    cancellable: bool = False
    timeout_seconds: int = 30
    rollback_tool: str = ""
    gateway: str = ""
    tags: tuple[str, ...] = ()
    handler: Any = None

    def with_handler(self, handler: Any) -> ToolDefinition:
        return ToolDefinition(
            name=self.name, description=self.description, version=self.version,
            input_schema=self.input_schema, output_schema=self.output_schema,
            permission=self.permission, capabilities=self.capabilities,
            required_capabilities=self.required_capabilities,
            requires_confirmation=self.requires_confirmation,
            confirmation_policy=self.confirmation_policy,
            destructive=self.destructive, idempotent=self.idempotent,
            cancellable=self.cancellable, timeout_seconds=self.timeout_seconds,
            rollback_tool=self.rollback_tool, gateway=self.gateway,
            tags=self.tags, handler=handler,
        )


@dataclass(frozen=True)
class ToolInvocation:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    invocation_id: str = ""
    correlation_id: str = ""
    started_at: str = ""
    timeout_seconds: int = 30


@dataclass(frozen=True)
class ToolExecutionResult:
    ok: bool
    tool_name: str
    data: dict[str, Any] | None = None
    error: str = ""
    code: ErrorCode = ErrorCode.OK
    duration_ms: float = 0.0
    correlation_id: str = ""


@dataclass(frozen=True)
class ActionPlan:
    plan_id: str
    session_id: str
    title: str = ""
    description: str = ""
    intent: str = ""
    steps: tuple[PlanStep, ...] = ()
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    requires_confirmation: bool = False
    confirmation_scope: str = ""
    rollback_strategy: str = "STOP"
    estimated_cost: str = ""
    estimated_duration: str = ""
    created_at: str = ""
    expires_at: str = ""


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    expected_result: str = ""
    on_failure: str = "STOP"
    rollback: str = ""
    timeout: int = 30
    cancellable: bool = False
    compensate: str = ""


@dataclass(frozen=True)
class PlanValidationResult:
    status: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class PlanState(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


@dataclass
class PlanExecution:
    plan: ActionPlan
    state: PlanState = PlanState.CREATED
    current_step_index: int = 0
    step_results: list[ToolExecutionResult] = field(default_factory=list)
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    correlation_id: str = ""


@dataclass(frozen=True)
class PlanExecutionResult:
    ok: bool
    state: PlanState
    plan_id: str
    step_results: tuple[ToolExecutionResult, ...] = ()
    error: str = ""
    code: ErrorCode = ErrorCode.OK
    duration_ms: float = 0.0
    correlation_id: str = ""


@dataclass(frozen=True)
class PlanRollbackResult:
    ok: bool
    rolled_back_steps: tuple[str, ...] = ()
    failed_steps: tuple[str, ...] = ()
    error: str = ""


@dataclass(frozen=True)
class ConfirmationRequest:
    confirmation_id: str
    plan_id: str
    summary: str = ""
    affected_resources: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    expires_at: str = ""
    single_use: bool = True
    required_phrase: str = ""
    plan: ActionPlan | None = None


@dataclass(frozen=True)
class Suggestion:
    id: str
    title: str
    description: str
    reason: str = ""
    priority: int = 5
    context_scope: str = ""
    action: str = ""
    action_args: dict[str, Any] = field(default_factory=dict)
    expires_at: str = ""
    deduplication_key: str = ""


@dataclass(frozen=True)
class ProviderRequest:
    messages: tuple[dict[str, Any], ...] = ()
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout_seconds: int = 30
    correlation_id: str = ""


@dataclass(frozen=True)
class ProviderResponse:
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    raw_size: int = 0
    parsed: dict[str, Any] = field(default_factory=dict)
    validation_errors: tuple[str, ...] = ()
    fallback_used: bool = False
    text: str = ""


@dataclass(frozen=True)
class AssistantTrace:
    trace_id: str
    session_id: str = ""
    request_id: str = ""
    intent: str = ""
    provider: str = ""
    plan_id: str = ""
    tools: tuple[str, ...] = ()
    durations: dict[str, float] = field(default_factory=dict)
    result_codes: tuple[str, ...] = ()
    fallbacks: tuple[str, ...] = ()
    cancellations: tuple[str, ...] = ()
    timestamp: str = ""


@dataclass(frozen=True)
class AssistantError:
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    message: str = ""
    details: str = ""
    correlation_id: str = ""
    recoverable: bool = False


class ProviderType(str, Enum):
    RULE = "RULE"
    LOCAL_MODEL = "LOCAL_MODEL"
    DISABLED = "DISABLED"


class CapabilityName(str, Enum):
    LIBRARY_READ = "library.read"
    LIBRARY_SEARCH = "library.search"
    LIBRARY_MODIFY = "library.modify"
    PLAYBACK_CONTROL = "playback.control"
    QUEUE_READ = "queue.read"
    QUEUE_MODIFY = "queue.modify"
    PLAYLIST_READ = "playlist.read"
    PLAYLIST_MODIFY = "playlist.modify"
    HISTORY_READ = "history.read"
    MIX_GENERATE = "mix.generate"
    RADIO_CONTROL = "radio.control"
    LYRICS_READ = "lyrics.read"
    METADATA_READ = "metadata.read"
    METADATA_MODIFY = "metadata.modify"
    AUDIO_LAB_ANALYZE = "audio_lab.analyze"
    AUDIO_LAB_CONVERT = "audio_lab.convert"
    AUDIO_LAB_REPLAYGAIN = "audio_lab.replaygain"
    LIBRARY_DOCTOR_SCAN = "library_doctor.scan"
    LIBRARY_DOCTOR_REPAIR = "library_doctor.repair"
    DEVICES_READ = "devices.read"
    DEVICES_SYNC = "devices.sync"
    CONNECTIONS_READ = "connections.read"
    CONNECTIONS_MODIFY = "connections.modify"
    HOME_AUDIO_READ = "home_audio.read"
    HOME_AUDIO_CONTROL = "home_audio.control"
    SETTINGS_READ = "settings.read"
    SETTINGS_MODIFY = "settings.modify"
    DIAGNOSTICS_READ = "diagnostics.read"
    NAVIGATION_REQUEST = "navigation.request"


class EntityType(str, Enum):
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"
    PLAYLIST = "playlist"
    GENRE = "genre"
    YEAR = "year"
    DECADE = "decade"
    DEVICE = "device"
    SETTING = "setting"
    SERVER = "server"
    OUTPUT = "output"
    FORMAT = "format"
    CODEC = "codec"
    BITRATE = "bitrate"
    SAMPLE_RATE = "sample_rate"
    BIT_DEPTH = "bit_depth"
    CHANNEL_MODE = "channel_mode"
    QUANTITY = "quantity"
    POSITION = "position"
    DURATION = "duration"
    PATH_REFERENCE = "path_reference"
    SCOPE = "scope"
    SORT = "sort"
    FILTER = "filter"


class IntentId(str, Enum):
    PLAY_TRACK = "play_track"
    PLAY_ALBUM = "play_album"
    PLAY_ARTIST = "play_artist"
    PLAY_PLAYLIST = "play_playlist"
    PLAY_MIX = "play_mix"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK = "seek"
    SET_VOLUME = "set_volume"
    SET_REPEAT = "set_repeat"
    SET_SHUFFLE = "set_shuffle"
    GET_QUEUE = "get_queue"
    ADD_TO_QUEUE = "add_to_queue"
    PLAY_NEXT = "play_next"
    REPLACE_QUEUE = "replace_queue"
    REMOVE_FROM_QUEUE = "remove_from_queue"
    CLEAR_QUEUE = "clear_queue"
    REORDER_QUEUE = "reorder_queue"
    SEARCH_LIBRARY = "search_library"
    GET_TRACK_DETAILS = "get_track_details"
    GET_ALBUM_DETAILS = "get_album_details"
    GET_ARTIST_DETAILS = "get_artist_details"
    LIST_RECENT = "list_recent_tracks"
    LIST_UNPLAYED = "list_unplayed_tracks"
    LIST_FAVORITES = "list_favorites"
    FIND_METADATA_GAPS = "find_metadata_gaps"
    LIST_PLAYLISTS = "list_playlists"
    GET_PLAYLIST = "get_playlist"
    DRAFT_PLAYLIST = "draft_playlist"
    CREATE_PLAYLIST = "create_playlist"
    ADD_TO_PLAYLIST = "add_to_playlist"
    REMOVE_FROM_PLAYLIST = "remove_from_playlist"
    REORDER_PLAYLIST = "reorder_playlist"
    CREATE_MIX = "create_smart_mix"
    EXPLAIN_MIX = "explain_mix"
    SAVE_MIX = "save_mix_as_playlist"
    CANCEL_MIX = "cancel_mix_generation"
    INSPECT_METADATA = "inspect_metadata"
    SUGGEST_METADATA = "suggest_metadata_changes"
    SCAN_HEALTH = "scan_library_health"
    PREVIEW_REPAIR = "preview_library_repair"
    APPLY_REPAIR = "apply_library_repair"
    PROBE_AUDIO = "probe_audio"
    ANALYZE_AUDIO = "analyze_audio"
    RECOMMEND_CONVERSION = "recommend_conversion_profile"
    PREVIEW_CONVERSION = "preview_conversion"
    START_CONVERSION = "start_conversion"
    CANCEL_CONVERSION = "cancel_conversion"
    ANALYZE_REPLAYGAIN = "analyze_replaygain"
    CHECK_INTEGRITY = "check_integrity"
    COMPARE_AUDIO = "compare_audio"
    DIAGNOSE_ECOSYSTEM = "diagnose_ecosystem"
    DIAGNOSE_SERVER = "diagnose_micro_server"
    DIAGNOSE_HOME_AUDIO = "diagnose_home_audio"
    DIAGNOSE_PAIRING = "diagnose_pairing"
    LIST_DEVICES = "list_devices"
    PLAN_SYNC = "plan_device_sync"
    START_SYNC = "start_device_sync"
    CANCEL_SYNC = "cancel_device_sync"
    GET_SETTING = "get_setting"
    SUGGEST_SETTING = "suggest_setting_change"
    PREVIEW_SETTING = "preview_setting_change"
    APPLY_SETTING = "apply_setting_change"
    NAVIGATE = "navigate"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"
