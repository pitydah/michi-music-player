"""ConfirmationService — token-based confirmation for destructive operations.

Model (P0 Fase Metadata extension): a destructive/sensitive operation may
ONLY execute with a verifiable authorization issued by ConfirmationService.
Self-declared sources (``confirmed=True`` + ``source="ui"/"doctor"/...``) are
NEVER accepted as authorization.

Two cooperating surfaces:

- ``ConfirmationRequest`` (legacy, S3): used by ActionRegistry and the
  preview->approve flows; ``confirm()``/``approve()``/``is_confirmed()``.
- ``ConfirmationToken`` (full token, P0): ``issue()`` creates a token bound
  to ``operation_id``, ``command_hash`` (the authorized context), ``target_hash``
  (the proposal/target entities), ``selected_fields`` (allowed field subset),
  an expiry, an ``approved`` flag, ``issuer`` (always ``confirmation_service``)
  and single-use consumption. ``validate()`` returns an explicit rejection
  code on any mismatch; ``consume()`` marks a single-use token as used.

A persisted audit log (JSONL) records issued/approved/consumed/rejected
tokens so tests and operators can validate the authorization trail.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Rejection codes (stable, actionable).
TOKEN_OK = "TOKEN_OK"
TOKEN_REQUIRED = "TOKEN_REQUIRED"
TOKEN_EXPIRED = "TOKEN_EXPIRED"
TOKEN_TARGET_MISMATCH = "TOKEN_TARGET_MISMATCH"
TOKEN_FIELD_MISMATCH = "TOKEN_FIELD_MISMATCH"
TOKEN_COMMAND_MISMATCH = "TOKEN_COMMAND_MISMATCH"
TOKEN_USED = "TOKEN_USED"
TOKEN_NOT_APPROVED = "TOKEN_NOT_APPROVED"

ISSUER = "confirmation_service"

_DEFAULT_TTL_S = 300


def compute_target_hash(targets) -> str:
    """Stable hash of the target entities (filepaths / track ids / refs)."""
    entries = []
    for target in targets or []:
        if isinstance(target, dict):
            entries.append(f"{target.get('filepath', '')}|{target.get('track_id', '')}")
        else:
            entries.append(str(target))
    payload = json.dumps({"targets": sorted(entries)}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ConfirmationToken:
    token_id: str
    operation_id: str
    command_hash: str
    target_hash: str
    selected_fields: tuple[str, ...] = ()
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + _DEFAULT_TTL_S)
    approved: bool = False
    issuer: str = ISSUER
    single_use: bool = True
    consumed: bool = False
    consumed_at: float | None = None
    rejected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "operation_id": self.operation_id,
            "command_hash": self.command_hash,
            "target_hash": self.target_hash,
            "selected_fields": list(self.selected_fields),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "approved": self.approved,
            "issuer": self.issuer,
            "single_use": self.single_use,
            "consumed": self.consumed,
            "consumed_at": self.consumed_at,
            "rejected": self.rejected,
        }


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
    def __init__(self, audit_path: str | None = None):
        logger.debug("ConfirmationService.__init__ called")
        self._pending: dict[str, ConfirmationRequest] = {}
        self._confirmed: dict[str, str] = {}
        self._tokens: dict[str, ConfirmationToken] = {}
        self._audit_path = audit_path
        self._in_memory_audit: list[dict[str, Any]] = []
        if audit_path:
            try:
                os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)
            except OSError:
                logger.debug("cannot create audit dir for %s", audit_path)

    # ── full token surface ───────────────────────────────────────────────

    def issue(self, operation_id: str, command_hash: str = "",
              target_hash: str = "", selected_fields: tuple[str, ...] = (),
              ttl: int = _DEFAULT_TTL_S, single_use: bool = True,
              token_id: str | None = None) -> ConfirmationToken:
        """Issue a verifiable token; the ONLY authorization source is this service."""
        token = ConfirmationToken(
            token_id=token_id or str(uuid.uuid4()).replace("-", ""),
            operation_id=operation_id,
            command_hash=command_hash,
            target_hash=target_hash or compute_target_hash([operation_id]),
            selected_fields=tuple(selected_fields or ()),
            issued_at=time.time(),
            expires_at=time.time() + max(1, int(ttl)),
            single_use=single_use,
        )
        self._tokens[token.token_id] = token
        self._audit("issued", token)
        return token

    def get_token(self, token_id: str) -> ConfirmationToken | None:
        return self._tokens.get(token_id)

    def list_tokens(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._tokens.values()]

    def approve_token(self, token_id: str) -> bool:
        """Approve a token issued via ``issue()`` (user confirmation step)."""
        token = self._tokens.get(token_id)
        if token is None or token.rejected:
            return False
        if time.time() > token.expires_at:
            return False
        if token.single_use and token.consumed:
            return False
        token.approved = True
        self._audit("approved", token)
        return True

    def validate(self, token_id: str, proposal=None,
                 requested_fields: tuple[str, ...] = (),
                 targets: tuple[Any, ...] = (),
                 *, command_hash: str = "", target_hash: str = "") -> tuple[bool, str]:
        """Validate a token against the requested operation.

        Any mismatch yields an explicit rejection code. A caller without a
        valid token gets ``TOKEN_REQUIRED``.
        """
        if not token_id:
            return False, TOKEN_REQUIRED
        token = self._tokens.get(token_id)
        if token is None:
            return False, TOKEN_REQUIRED
        if token.single_use and token.consumed:
            return False, TOKEN_USED
        if time.time() > token.expires_at:
            return False, TOKEN_EXPIRED
        if not token.approved:
            return False, TOKEN_NOT_APPROVED

        expected_target = target_hash
        if not expected_target and targets:
            expected_target = compute_target_hash(targets)
        if not expected_target:
            refs = getattr(proposal, "track_refs", None) or []
            expected_target = compute_target_hash(refs)
        if expected_target and token.target_hash and expected_target != token.target_hash:
            return False, TOKEN_TARGET_MISMATCH

        expected_cmd = command_hash or getattr(proposal, "command_hash", "") or ""
        if expected_cmd and token.command_hash and expected_cmd != token.command_hash:
            return False, TOKEN_COMMAND_MISMATCH

        requested = tuple(requested_fields or ())
        if token.selected_fields and requested:
            allowed = set(token.selected_fields)
            if not set(requested).issubset(allowed):
                return False, TOKEN_FIELD_MISMATCH
        return True, TOKEN_OK

    def consume(self, token_id: str) -> bool:
        """Mark a single-use token as consumed (idempotent)."""
        token = self._tokens.get(token_id)
        if token is None:
            return False
        if not token.single_use:
            return True
        if token.consumed:
            return False
        token.consumed = True
        token.consumed_at = time.time()
        self._audit("consumed", token)
        return True

    def audit_log(self) -> list[dict[str, Any]]:
        """Read back the persisted audit log (or the in-memory one)."""
        if self._audit_path and os.path.isfile(self._audit_path):
            entries = []
            try:
                with open(self._audit_path, encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except ValueError:
                                continue
                return entries
            except OSError:
                return list(self._in_memory_audit)
        return list(self._in_memory_audit)

    # ── legacy request/approve surface (S3, kept for ActionRegistry) ─────

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
        """Create a confirmation bound to a command hash and entities.

        Also issues the full token (target_hash derived from the entity refs /
        target) so the same token works with ``approve()`` and ``validate()``.
        """
        req = self.request(
            operation_id=operation_id,
            target=target or operation_id,
            description=description,
            command_hash=command_hash,
            entity_refs=entity_refs,
            risk_level=risk_level,
            single_use=single_use,
        )
        self.issue(
            operation_id=operation_id,
            command_hash=command_hash,
            target_hash=compute_target_hash(entity_refs or [target or operation_id]),
            single_use=single_use,
            token_id=req.token,
        )
        return req

    def approve(self, token: str) -> ConfirmationRequest | None:
        req = self._pending.get(token)
        if req is not None:
            if req.resolved:
                return None
            elapsed = time.monotonic() - req.created_at
            if elapsed > req.expiry_s:
                self._pending.pop(token, None)
                return None
            req.resolved = True
            req.approved = True
            self._confirmed[req.operation_id] = req.command_hash
            full = self._tokens.get(token)
            if full is not None:
                full.approved = True
                self._audit("approved", full)
            return req
        # Token issued via issue() (editor pipeline): approve the full token.
        full = self._tokens.get(token)
        if full is None or full.rejected:
            return None
        if full.single_use and full.consumed:
            return None
        if time.time() > full.expires_at:
            return None
        full.approved = True
        self._audit("approved", full)
        synthetic = ConfirmationRequest(
            operation_id=full.operation_id,
            target=full.target_hash,
            command_hash=full.command_hash,
        )
        synthetic.token = token
        synthetic.resolved = True
        synthetic.approved = True
        return synthetic

    def reject(self, token: str) -> bool:
        req = self._pending.pop(token, None)
        if req is None:
            return False
        req.resolved = True
        req.approved = False
        full = self._tokens.get(token)
        if full is not None:
            full.rejected = True
            self._audit("rejected", full)
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
        now_epoch = time.time()
        for token_id, tok in list(self._tokens.items()):
            if now_epoch > tok.expires_at:
                self._tokens.pop(token_id, None)

    def shutdown(self):
        self._pending.clear()
        self._confirmed.clear()
        self._tokens.clear()

    def health(self) -> dict:
        return {
            "available": True,
            "pending": len(self._pending),
            "tokens_active": len(self._tokens),
            "audit_persisted": bool(self._audit_path),
        }

    # ── audit trail ──────────────────────────────────────────────────────

    def _audit(self, event: str, token: ConfirmationToken) -> None:
        record = {
            "event": event,
            "token_id": token.token_id,
            "operation_id": token.operation_id,
            "command_hash": token.command_hash,
            "target_hash": token.target_hash,
            "selected_fields": list(token.selected_fields),
            "single_use": token.single_use,
            "ts": time.time(),
        }
        self._in_memory_audit.append(record)
        if not self._audit_path:
            return
        try:
            with open(self._audit_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            logger.debug("confirmation audit append failed", exc_info=True)

    def start(self) -> None:
        """Container lifecycle hook (idempotent no-op)."""

    def set_audit_path(self, path: str | None) -> None:
        self._audit_path = path
