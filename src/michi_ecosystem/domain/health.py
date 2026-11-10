"""Health domain: canonical states, issue codes and repair actions (E8).

Raw exceptions never reach the primary UI (docs/ux/error-copy.md); ``available``
is never conflated with ``healthy`` (master plan §51).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ACTION_REQUIRED = "action_required"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class HealthIssue:
    code: str
    severity: IssueSeverity
    title: str
    detail: str = ""
    repair_route: str = ""
    repair_label: str = ""


@dataclass(frozen=True)
class HealthSummary:
    state: HealthState
    issues: tuple[HealthIssue, ...] = ()

    @property
    def errors(self) -> tuple[HealthIssue, ...]:
        return tuple(
            issue for issue in self.issues if issue.severity is IssueSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[HealthIssue, ...]:
        return tuple(
            issue for issue in self.issues if issue.severity is IssueSeverity.WARNING
        )
