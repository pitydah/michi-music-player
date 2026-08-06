"""UndoService — operation log with real compensation callbacks (ADR-005).

An operation registers a compensation once its side effects are confirmed;
``undo(operation_id)`` invokes the compensation and records the outcome.
Compensations run synchronously on the caller thread and must be idempotent;
failures are reported (UNDO_FAILED), never swallowed.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.models.operation_result import OperationResult

logger = logging.getLogger("michi.undo")

EVENT_UNDO_REGISTERED = "undo.registered"
EVENT_UNDO_EXECUTED = "undo.executed"
EVENT_UNDO_FAILED = "undo.failed"

UNDO_STATE_REGISTERED = "registered"
UNDO_STATE_UNDONE = "undone"
UNDO_STATE_FAILED = "failed"


@dataclass
class UndoEntry:
    operation_id: str
    description: str
    compensate: Callable[[], Any]
    entity: str = ""
    kind: str = ""
    created_at: float = field(default_factory=time.time)
    state: str = UNDO_STATE_REGISTERED
    undone_at: float | None = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "description": self.description,
            "entity": self.entity,
            "kind": self.kind,
            "created_at": self.created_at,
            "state": self.state,
            "undone_at": self.undone_at,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class UndoService:
    """In-memory compensation log shared by metadata editor and library doctor."""

    def __init__(self, event_bus: Any | None = None, max_entries: int = 200):
        self._lock = threading.Lock()
        self._entries: dict[str, UndoEntry] = {}
        self._event_bus = event_bus
        self._max_entries = max_entries

    def register(self, operation_id: str, description: str,
                 compensate: Callable[[], Any], *,
                 entity: str = "", kind: str = "",
                 metadata: dict[str, Any] | None = None) -> OperationResult:
        """Register a compensation for a confirmed operation."""
        if not operation_id:
            return OperationResult.fail("INVALID_OPERATION_ID",
                                        "operation_id must be non-empty")
        if not callable(compensate):
            return OperationResult.fail("INVALID_COMPENSATION",
                                        "compensate must be callable")
        entry = UndoEntry(
            operation_id=operation_id,
            description=description or operation_id,
            compensate=compensate,
            entity=entity,
            kind=kind,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._entries[operation_id] = entry
            if len(self._entries) > self._max_entries:
                oldest = sorted(
                    self._entries.values(), key=lambda e: e.created_at,
                )[0]
                self._entries.pop(oldest.operation_id, None)
        self._emit(EVENT_UNDO_REGISTERED, {
            "operation_id": operation_id,
            "description": entry.description,
            "kind": kind,
        })
        return OperationResult.success({
            "operation_id": operation_id,
            "description": entry.description,
        })

    def can_undo(self, operation_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(operation_id)
            return entry is not None and entry.state == UNDO_STATE_REGISTERED

    def describe(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._entries.get(operation_id)
            return entry.to_dict() if entry else None

    def undo(self, operation_id: str, reason: str = "user") -> OperationResult:
        """Run the registered compensation for an operation (real undo)."""
        with self._lock:
            entry = self._entries.get(operation_id)
            if entry is None:
                return OperationResult.fail("UNDO_NOT_FOUND",
                                            f"No operation logged: {operation_id}")
            if entry.state != UNDO_STATE_REGISTERED:
                return OperationResult.fail(
                    "UNDO_STATE",
                    f"Operation {operation_id} is {entry.state}",
                )
        try:
            outcome = entry.compensate()
        except Exception as error:  # noqa: BLE001
            logger.exception("Undo failed for %s", operation_id)
            with self._lock:
                entry.state = UNDO_STATE_FAILED
                entry.error = str(error)
            self._emit(EVENT_UNDO_FAILED, {
                "operation_id": operation_id,
                "error": str(error),
            })
            return OperationResult.fail("UNDO_FAILED", str(error))
        with self._lock:
            entry.state = UNDO_STATE_UNDONE
            entry.undone_at = time.time()
            if isinstance(outcome, dict):
                entry.metadata.update(outcome)
        self._emit(EVENT_UNDO_EXECUTED, {
            "operation_id": operation_id,
            "description": entry.description,
            "kind": entry.kind,
            "reason": reason,
        })
        return OperationResult.success({
            "operation_id": operation_id,
            "description": entry.description,
            "entity": entry.entity,
            "kind": entry.kind,
            "compensated": True,
        })

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            entries = sorted(
                self._entries.values(), key=lambda e: e.created_at, reverse=True,
            )
            return [e.to_dict() for e in entries[:limit]]

    def forget(self, operation_id: str) -> bool:
        with self._lock:
            return self._entries.pop(operation_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self._event_bus is None or not hasattr(self._event_bus, "emit"):
            return
        try:
            self._event_bus.emit(event, data)
        except Exception:  # noqa: BLE001
            logger.debug("undo event emit failed", exc_info=True)

    def health(self) -> dict:
        return {"available": True, "registered": len(self._entries),
                "max_entries": self._max_entries}

    def start(self) -> None:
        """Container lifecycle hook (idempotent no-op)."""

    def shutdown(self) -> None:
        self.clear()
