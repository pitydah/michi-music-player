"""Canonical contracts shared by Audio Lab orchestration, services, and QML."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Any, Mapping


class AudioLabOperation(StrEnum):
    PROBE = "probe"
    ANALYSIS = "analysis"
    CONVERSION = "conversion"
    NORMALIZATION = "normalization"
    REPLAYGAIN = "replaygain"
    INTEGRITY = "integrity"
    COMPARISON = "comparison"
    BATCH = "batch"
    CD_TRACK = "cd_track"
    CD_ALBUM = "cd_album"
    ADC_POSTPROCESS = "adc_postprocess"


class AudioLabJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class AudioLabErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVALID_PROFILE = "INVALID_PROFILE"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
    OPERATION_FAILED = "OPERATION_FAILED"
    CANCELLED = "CANCELLED"
    UNSUPPORTED = "UNSUPPORTED"


class AudioLabCapabilityStatus(StrEnum):
    AVAILABLE = "available"
    CONFIGURATION_REQUIRED = "configuration_required"
    DEPENDENCY_MISSING = "dependency_missing"
    EXPERIMENTAL = "experimental"
    HARDWARE_NOT_DETECTED = "hardware_not_detected"
    PLATFORM_UNAVAILABLE = "platform_unavailable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class AudioLabCapability:
    id: str
    available: bool
    status: AudioLabCapabilityStatus
    reason: str = ""
    dependencies: tuple[str, ...] = ()
    platform: str = ""

    def to_qml(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["dependencies"] = list(self.dependencies)
        return result


@dataclass(frozen=True, slots=True)
class AudioLabOperationResult:
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    job_id: str = ""
    status: str = ""
    error_code: str = ""
    message: str = ""
    detail: str = ""
    recoverable: bool = False
    requires_confirmation: bool = False
    confirmation_token: str = ""
    warning: str = ""
    operation: str = ""

    @classmethod
    def immediate(cls, result: Mapping[str, Any] | None = None) -> AudioLabOperationResult:
        return cls(ok=True, result=dict(result or {}))

    @classmethod
    def queued(cls, job_id: str) -> AudioLabOperationResult:
        return cls(ok=True, job_id=job_id, status=AudioLabJobStatus.QUEUED.value)

    @classmethod
    def failure(
        cls,
        code: AudioLabErrorCode | str,
        message: str,
        *,
        detail: str = "",
        recoverable: bool = False,
    ) -> AudioLabOperationResult:
        return cls(
            ok=False,
            error_code=str(code),
            message=message,
            detail=detail,
            recoverable=recoverable,
        )

    @classmethod
    def confirmation(
        cls, operation: AudioLabOperation | str, token: str, warning: str
    ) -> AudioLabOperationResult:
        return cls(
            ok=False,
            error_code=AudioLabErrorCode.CONFIRMATION_REQUIRED.value,
            message=warning,
            requires_confirmation=True,
            confirmation_token=token,
            warning=warning,
            operation=str(operation),
        )

    def to_qml(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AudioLabJobSnapshot:
    job_id: str
    operation: AudioLabOperation
    status: AudioLabJobStatus = AudioLabJobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    request: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] = field(default_factory=dict)
    task_id: str = ""
    service_job_id: str = ""
    attempt: int = 1
    created_at: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0

    def set_progress(self, value: float, message: str = "") -> None:
        if not isfinite(value) or value < self.progress or not 0.0 <= value <= 1.0:
            raise ValueError("Audio Lab progress must be finite, monotonic, and between 0 and 1")
        self.progress = value
        if message:
            self.message = message

    def to_qml(self) -> dict[str, Any]:
        result = asdict(self)
        result["operation"] = self.operation.value
        result["status"] = self.status.value
        return result


@dataclass(frozen=True, slots=True)
class ConversionProfile:
    id: str = ""
    name: str = "Custom"
    format: str = "FLAC"
    codec: str = ""
    bitrate: int = 0
    vbr_quality: float | None = None
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    copy_metadata: bool = True
    copy_artwork: bool = True
    apply_replaygain: bool = False
    output_dir: str = ""
    filename_template: str = "{artist} - {title}"
    collision_policy: str = "rename"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ConversionProfile:
        data = dict(value)
        if "preserve_metadata" in data and "copy_metadata" not in data:
            data["copy_metadata"] = data.pop("preserve_metadata")
        if "preserve_artwork" in data and "copy_artwork" not in data:
            data["copy_artwork"] = data.pop("preserve_artwork")
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: data[key] for key in allowed if key in data})

    def to_qml(self) -> dict[str, Any]:
        return asdict(self)
