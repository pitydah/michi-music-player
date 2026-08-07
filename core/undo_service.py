"""UndoService — operation log with real compensation callbacks (ADR-005).

An operation registers a compensation once its side effects are confirmed;
``undo(operation_id)`` invokes the compensation and records the outcome.
Compensations run synchronously on the caller thread and must be idempotent;
failures are reported (UNDO_FAILED), never swallowed.

Persistence (P0 Fase Metadata): every registration may carry serializable
``compensation_data`` (previous values, backup references, entity refs).
With a ``persistence_path`` (JSONL) the record survives restarts; a fresh
UndoService over the same store can undo(operation_id) by compensating from
the persisted data (DB restore via the bound mutation service, physical
restore from the backup reference when present).
"""
from __future__ import annotations

import json
import logging
import os
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
    compensate: Callable[[], Any] | None = None
    entity: str = ""
    kind: str = ""
    created_at: float = field(default_factory=time.time)
    state: str = UNDO_STATE_REGISTERED
    undone_at: float | None = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    compensation_data: dict[str, Any] | None = None

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
            "compensation_data": dict(self.compensation_data)
            if self.compensation_data else None,
        }


class UndoService:
    """Compensation log shared by metadata editor and library doctor.

    With ``persistence_path`` every register/undo/forget is appended to a
    JSONL store and replayed on construction, so undo survives restarts when
    the compensation can be rebuilt from ``compensation_data`` (bound
    ``db``/``mutation_service`` restore DB previous values; backup references
    restore physical tags).
    """

    def __init__(self, event_bus: Any | None = None, max_entries: int = 200,
                 persistence_path: str | None = None,
                 db: Any | None = None,
                 mutation_service: Any | None = None):
        self._lock = threading.Lock()
        self._entries: dict[str, UndoEntry] = {}
        self._event_bus = event_bus
        self._max_entries = max_entries
        self._persistence_path = persistence_path
        self._db = db
        self._mutation = mutation_service
        if persistence_path:
            try:
                os.makedirs(os.path.dirname(persistence_path) or ".",
                            exist_ok=True)
            except OSError:
                logger.debug("cannot create undo store dir for %s",
                             persistence_path)
            self._replay()

    def bind_db(self, db: Any, mutation_service: Any | None = None) -> None:
        """Late wiring: DB restore surface used for persisted compensations."""
        self._db = db
        if mutation_service is not None:
            self._mutation = mutation_service

    def register(self, operation_id: str, description: str,
                 compensate: Callable[[], Any] | None, *,
                 entity: str = "", kind: str = "",
                 metadata: dict[str, Any] | None = None,
                 compensation_data: dict[str, Any] | None = None) -> OperationResult:
        """Register a compensation for a confirmed operation."""
        if not operation_id:
            return OperationResult.fail("INVALID_OPERATION_ID",
                                        "operation_id must be non-empty")
        if compensate is None and not compensation_data:
            return OperationResult.fail("INVALID_COMPENSATION",
                                        "compensate or compensation_data "
                                        "must be provided")
        entry = UndoEntry(
            operation_id=operation_id,
            description=description or operation_id,
            compensate=compensate,
            entity=entity,
            kind=kind,
            metadata=dict(metadata or {}),
            compensation_data=dict(compensation_data or {})
            if compensation_data else None,
        )
        with self._lock:
            self._entries[operation_id] = entry
            if len(self._entries) > self._max_entries:
                oldest = sorted(
                    self._entries.values(), key=lambda e: e.created_at,
                )[0]
                self._entries.pop(oldest.operation_id, None)
        self._persist("register", entry)
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
            if entry.compensate is not None:
                outcome = entry.compensate()
            elif entry.compensation_data:
                outcome = self._compensate_from_data(entry.compensation_data)
            else:
                outcome = {"restored": 0,
                           "errors": ["no compensation available"]}
            errors = outcome.get("errors") if isinstance(outcome, dict) else []
            if errors:
                raise RuntimeError("; ".join(str(e) for e in errors))
        except Exception as error:  # noqa: BLE001
            logger.exception("Undo failed for %s", operation_id)
            with self._lock:
                entry.state = UNDO_STATE_FAILED
                entry.error = str(error)
            self._persist("undo", entry)
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
        self._persist("undo", entry)
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

    def _compensate_from_data(self, data: dict[str, Any]) -> dict:
        """Generic compensation from persisted data (restart-safe undo)."""
        restored = 0
        errors: list[str] = []
        for track in data.get("tracks") or []:
            try:
                track_id = track.get("track_id")
                old_values = track.get("old_values") or {}
                if track_id is not None and old_values:
                    self._restore_db(track_id, old_values)
                backup = track.get("backup_path") or ""
                filepath = track.get("filepath") or ""
                if backup and filepath and os.path.isfile(backup):
                    import shutil
                    shutil.copy2(backup, filepath)
                    os.unlink(backup)
                restored += 1
            except Exception as error:  # noqa: BLE001
                errors.append(str(error))
        return {"restored": restored, "errors": errors}

    def _restore_db(self, track_id: int, old_values: dict) -> None:
        if self._mutation is not None and hasattr(self._mutation,
                                                  "update_media_fields"):
            result = self._mutation.update_media_fields(track_id, old_values)
            if isinstance(result, OperationResult) and not result.ok:
                raise RuntimeError(result.message or result.code)
            return
        if self._db is not None and hasattr(self._db, "update_media_item_field"):
            for field, value in old_values.items():
                if not self._db.update_media_item_field(track_id, field, value):
                    raise RuntimeError(f"restore failed for {field}")
            return
        conn = getattr(self._db, "conn", None)
        if conn is None:
            raise RuntimeError("no DB restore surface bound")
        with conn:
            for field, value in old_values.items():
                conn.execute(
                    f"UPDATE media_items SET {field}=? WHERE id=?",
                    (value, track_id),
                )

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            entries = sorted(
                self._entries.values(), key=lambda e: e.created_at, reverse=True,
            )
            return [e.to_dict() for e in entries[:limit]]

    def forget(self, operation_id: str) -> bool:
        with self._lock:
            entry = self._entries.pop(operation_id, None)
        if entry is not None:
            self._persist("forget", entry)
        return entry is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _persist(self, op: str, entry: UndoEntry) -> None:
        if not self._persistence_path:
            return
        record = {"op": op, "entry": entry.to_dict()}
        try:
            with open(self._persistence_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            logger.debug("undo persistence append failed", exc_info=True)

    def _replay(self) -> None:
        if not self._persistence_path or not os.path.isfile(self._persistence_path):
            return
        try:
            with open(self._persistence_path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    entry_dict = record.get("entry") or {}
                    op = record.get("op", "register")
                    op_id = entry_dict.get("operation_id", "")
                    if not op_id:
                        continue
                    if op == "forget":
                        self._entries.pop(op_id, None)
                        continue
                    entry = UndoEntry(
                        operation_id=op_id,
                        description=entry_dict.get("description", op_id),
                        compensate=None,
                        entity=entry_dict.get("entity", ""),
                        kind=entry_dict.get("kind", ""),
                        created_at=entry_dict.get("created_at", time.time()),
                        state=entry_dict.get("state", UNDO_STATE_REGISTERED),
                        undone_at=entry_dict.get("undone_at"),
                        error=entry_dict.get("error", ""),
                        metadata=entry_dict.get("metadata") or {},
                        compensation_data=entry_dict.get("compensation_data"),
                    )
                    if op == "undo" and entry.state == UNDO_STATE_REGISTERED:
                        entry.state = UNDO_STATE_UNDONE
                    self._entries[op_id] = entry
        except OSError:
            logger.debug("undo persistence replay failed", exc_info=True)

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self._event_bus is None or not hasattr(self._event_bus, "emit"):
            return
        try:
            self._event_bus.emit(event, data)
        except Exception:  # noqa: BLE001
            logger.debug("undo event emit failed", exc_info=True)

    def health(self) -> dict:
        return {"available": True, "registered": len(self._entries),
                "max_entries": self._max_entries,
                "persistence": bool(self._persistence_path)}

    def start(self) -> None:
        """Container lifecycle hook (idempotent no-op)."""

    def shutdown(self) -> None:
        self.clear()
