from __future__ import annotations

from enum import Enum


class MetadataErrorCode(Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    FILE_NOT_FOUND = "file_not_found"
    NOT_A_FILE = "not_a_file"
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    READ_FAILED = "read_failed"
    WRITE_FAILED = "write_failed"
    VERIFY_FAILED = "verify_failed"
    BACKUP_FAILED = "backup_failed"
    ROLLBACK_FAILED = "rollback_failed"
    INVALID_METADATA = "invalid_metadata"
    INVALID_FIELD = "invalid_field"
    INVALID_VALUE = "invalid_value"
    INVALID_PATH = "invalid_path"
    FILE_CHANGED = "file_changed"
    PERMISSION_DENIED = "permission_denied"
    READ_ONLY_FILESYSTEM = "read_only_filesystem"
    PROVIDER_DISABLED = "provider_disabled"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_INVALID_RESPONSE = "provider_invalid_response"
    NO_MATCH = "no_match"
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_MATCH = "ambiguous_match"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CANCELLED = "cancelled"
    STALE_RESULT = "stale_result"
    PARTIAL_SUCCESS = "partial_success"
    DATABASE_FAILED = "database_failed"
    JOURNAL_FAILED = "journal_failed"
    INTERNAL_ERROR = "internal_error"


class FieldOperation(Enum):
    SET = "set"
    CLEAR = "clear"
    APPEND = "append"
    REMOVE = "remove"
    REPLACE = "replace"
    MERGE = "merge"


class BackupPolicy(Enum):
    NONE = "none"
    SIDECAR_SNAPSHOT = "sidecar_snapshot"
    FULL_FILE_BACKUP = "full_file_backup"
    FORMAT_NATIVE_WHEN_AVAILABLE = "format_native_when_available"


class MatchClassification(Enum):
    EXACT = "exact"
    HIGH_CONFIDENCE = "high_confidence"
    AMBIGUOUS = "ambiguous"
    LOW_CONFIDENCE = "low_confidence"
    NO_MATCH = "no_match"


class ReviewStatus(Enum):
    DRAFT = "draft"
    READY = "ready"
    APPROVED = "approved"
    APPLYING = "applying"
    APPLIED = "applied"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class BatchPolicy(Enum):
    ALL_OR_NOTHING = "all_or_nothing"
    BEST_EFFORT = "best_effort"
    STOP_ON_FIRST_FAILURE = "stop_on_first_failure"


class FileConsistency(Enum):
    CONSISTENT = "consistent"
    DB_NEWER = "db_newer"
    FILE_NEWER = "file_newer"
    FILE_MISSING = "file_missing"
    DB_MISSING = "db_missing"
    TAGS_CORRUPT = "tags_corrupt"
    SIGNATURE_MISMATCH = "signature_mismatch"
    UNKNOWN = "unknown"


class DuplicateLevel(Enum):
    EXACT_FILE_DUPLICATE = "exact_file_duplicate"
    EXACT_AUDIO_DUPLICATE = "exact_audio_duplicate"
    SAME_RECORDING = "same_recording"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    DIFFERENT_VERSION = "different_version"
    NOT_A_DUPLICATE = "not_a_duplicate"


class JournalStatus(Enum):
    PLANNED = "planned"
    PREFLIGHTED = "preflighted"
    BACKED_UP = "backed_up"
    WRITING = "writing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"
    CANCELLED = "cancelled"
