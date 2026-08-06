"""ConfirmationService — token-based confirmation for destructive operations.

Model (per ADR 4.27 extension for Slice 3): a request carries an operation id,
a command hash (bound to the ActionContext it authorizes), entity references,
a risk level and a single-use flag. ``is_confirmed(operation_id, hash)`` is
the check used by ActionRegistry before executing a destructive action with
an explicit context; a previously confirmed hash that differs from the
requested one means the selection/context changed and the confirmation is
invalid (CONFIRMATION_MISMATCH).
"""
from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger(__name__)


class ConfirmationRequest:
    def __init__(self, operation_id: str, target: str,
                 description: str = "", field_count: int = 0,
                 requires_backup: bool = True,
                 expiry_s: int = 120,
                 command_hash: str = "",
                 entity_refs: tuple[str, ...] = (),
                 risk_level: str = "high",
                 single_use: bool = True):
        self.token = str(uuid.uuid4())[:16]
        self.operation_id = operation_id
        self.target = target
        self.description = description
        self.field_count = field_count
        self.requires_backup = requires_backup
        self.expiry_s = expiry_s
        self.command_hash = command_hash
        self.entity_refs = tuple(entity_refs)
        self.risk_level = risk_level
        self.single_use = single_use
        self.created_at = time.monotonic()
        self.resolved = False
        self.approved = False


class ConfirmationService:
    def __init__(self):
        logger.debug("ConfirmationService.__init__ called")
        self._pending: dict[str, ConfirmationRequest] = {}
        self._confirmed: dict[str, str] = {}

    def request(self, operation_id: str, target: str,
                description: str = "",
                field_count: int = 0,
                requires_backup: bool = True,
                command_hash: str = "",
                entity_refs: tuple[str, ...] = (),
                risk_level: str = "high",
                single_use: bool = True) -> ConfirmationRequest:
        """Create a pending confirmation request (backward-compatible API)."""
        req = ConfirmationRequest(
            operation_id=operation_id,
            target=target,
            description=description or f"Modificar metadatos de {target}",
            field_count=field_count,
            requires_backup=requires_backup,
            command_hash=command_hash,
            entity_refs=entity_refs,
            risk_level=risk_level,
            single_use=single_use,
        )
        self._pending[req.token] = req
        return req

    def confirm(self, operation_id: str, command_hash: str = "",
                entity_refs: tuple[str, ...] = (),
                risk_level: str = "high",
                single_use: bool = True,
                description: str = "",
                target: str = "") -> ConfirmationRequest:
        """Create a confirmation bound to a command hash and entities."""
        return self.request(
            operation_id=operation_id,
            target=target or operation_id,
            description=description,
            command_hash=command_hash,
            entity_refs=entity_refs,
            risk_level=risk_level,
            single_use=single_use,
        )

    def approve(self, token: str) -> ConfirmationRequest | None:
        req = self._pending.get(token)
        if req is None:
            return None
        if req.resolved:
            return None
        elapsed = time.monotonic() - req.created_at
        if elapsed > req.expiry_s:
            self._pending.pop(token, None)
            return None
        req.resolved = True
        req.approved = True
        self._confirmed[req.operation_id] = req.command_hash
        return req

    def reject(self, token: str) -> bool:
        req = self._pending.pop(token, None)
        if req is None:
            return False
        req.resolved = True
        req.approved = False
        return True

    def is_confirmed(self, operation_id: str, context_hash: str) -> bool:
        return self.confirmed_hash(operation_id) == context_hash

    def confirmed_hash(self, operation_id: str) -> str | None:
        return self._confirmed.get(operation_id)

    def revoke(self, operation_id: str):
        for token, req in list(self._pending.items()):
            if req.operation_id == operation_id:
                self._pending.pop(token, None)
        self._confirmed.pop(operation_id, None)

    def cleanup_expired(self):
        now = time.monotonic()
        for token, req in list(self._pending.items()):
            if now - req.created_at > req.expiry_s:
                self._pending.pop(token, None)

    def shutdown(self):
        self._pending.clear()
        self._confirmed.clear()
