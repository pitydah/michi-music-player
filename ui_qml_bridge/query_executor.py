"""Backward-compat import stub — QueryExecutor moved to core.query_executor."""
from __future__ import annotations

from core.query_executor import QueryExecutor  # noqa: F401
from core.query_executor import RequestRecord  # noqa: F401
from core.query_executor import (
    STATE_QUEUED, STATE_RUNNING, STATE_COMPLETED,
    STATE_CANCEL_REQUESTED, STATE_CANCELLED, STATE_FAILED,
    STATE_STALE, STATE_SHUTDOWN,
)

__all__ = [
    "QueryExecutor", "RequestRecord",
    "STATE_QUEUED", "STATE_RUNNING", "STATE_COMPLETED",
    "STATE_CANCEL_REQUESTED", "STATE_CANCELLED", "STATE_FAILED",
    "STATE_STALE", "STATE_SHUTDOWN",
]
