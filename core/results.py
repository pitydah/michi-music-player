from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationResult:
    ok: bool = True
    code: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = False
    retryable: bool = False
    requires_confirmation: bool = False
    job_id: str = ""
    affected_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class OperationError(OperationResult):
    ok: bool = False


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class JobResult:
    ok: bool = True
    job_id: str = ""
    progress: float = 0.0
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
