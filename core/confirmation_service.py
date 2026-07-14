"""ConfirmationService — token-based confirmation for destructive operations."""
from __future__ import annotations

import time
import uuid


class ConfirmationRequest:
    def __init__(self, operation_id: str, target: str,
                 description: str, field_count: int = 0,
                 requires_backup: bool = True,
                 expiry_s: int = 120):
        self.token = str(uuid.uuid4())[:16]
        self.operation_id = operation_id
        self.target = target
        self.description = description
        self.field_count = field_count
        self.requires_backup = requires_backup
        self.expiry_s = expiry_s
        self.created_at = time.monotonic()
        self.resolved = False
        self.approved = False


class ConfirmationService:
    def __init__(self):
        self._pending: dict[str, ConfirmationRequest] = {}

    def request(self, operation_id: str, target: str,
                description: str = "",
                field_count: int = 0,
                requires_backup: bool = True) -> ConfirmationRequest:
        req = ConfirmationRequest(
            operation_id=operation_id,
            target=target,
            description=description or f"Modificar metadatos de {target}",
            field_count=field_count,
            requires_backup=requires_backup,
        )
        self._pending[req.token] = req
        return req

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
        return req

    def reject(self, token: str) -> bool:
        req = self._pending.pop(token, None)
        if req is None:
            return False
        req.resolved = True
        req.approved = False
        return True

    def revoke(self, operation_id: str):
        for token, req in list(self._pending.items()):
            if req.operation_id == operation_id:
                self._pending.pop(token, None)

    def cleanup_expired(self):
        now = time.monotonic()
        for token, req in list(self._pending.items()):
            if now - req.created_at > req.expiry_s:
                self._pending.pop(token, None)

    def shutdown(self):
        self._pending.clear()
