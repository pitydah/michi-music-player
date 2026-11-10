"""Single-use flash approvals (F0.1).

An ``ApprovedFlashPlan`` is valid exactly once: the registry consumes it
atomically before the first destructive action. Reuse, TTL expiry and binding
drift are explicit states (APPROVED → CONSUMED / INVALIDATED / EXPIRED) and a
failed consume never touches hardware.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from michi_ecosystem.domain.flashing import ApprovedFlashPlan


class ApprovalState(StrEnum):
    APPROVED = "approved"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


DEFAULT_TTL_MS = 10 * 60 * 1000


def _now_ms() -> int:
    """Monotonic clock: TTL must not depend on system clock changes."""
    return time.monotonic_ns() // 1_000_000


class ApprovalError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass
class _Entry:
    device_fingerprint: str
    manifest_digest: str
    mode: str
    provisioning_fingerprint: str
    state: ApprovalState
    created_at_ms: int


class ApprovalRegistry:
    """Thread-safe ledger of approved flash operations (single use)."""

    def __init__(
        self,
        *,
        ttl_ms: int = DEFAULT_TTL_MS,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._ttl_ms = ttl_ms
        self._clock = clock or _now_ms
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def register(self, approved: ApprovedFlashPlan) -> None:
        with self._lock:
            if approved.approval_id in self._entries:
                raise ApprovalError(
                    "APPROVAL_DUPLICATE",
                    "approval id ya registrado",
                )
            self._entries[approved.approval_id] = _Entry(
                device_fingerprint=approved.device_fingerprint,
                manifest_digest=approved.manifest_digest,
                mode=approved.plan.mode.value,
                provisioning_fingerprint=approved.provisioning_fingerprint,
                state=ApprovalState.APPROVED,
                created_at_ms=self._clock(),
            )

    def state(self, approval_id: str) -> ApprovalState | None:
        with self._lock:
            entry = self._entries.get(approval_id)
            return entry.state if entry is not None else None

    def invalidate(self, approval_id: str) -> None:
        with self._lock:
            entry = self._entries.get(approval_id)
            if entry is not None and entry.state is ApprovalState.APPROVED:
                entry.state = ApprovalState.INVALIDATED

    def consume(self, approved: ApprovedFlashPlan) -> None:
        """Atomically consume an approval before any destructive action."""
        with self._lock:
            entry = self._entries.get(approved.approval_id)
            if entry is None:
                raise ApprovalError("UNKNOWN_APPROVAL", "la aprobación no existe")
            if entry.state is ApprovalState.CONSUMED:
                raise ApprovalError(
                    "APPROVAL_ALREADY_CONSUMED",
                    "esta aprobación ya fue usada; prepará el flasheo de nuevo",
                )
            if entry.state is ApprovalState.INVALIDATED:
                raise ApprovalError(
                    "APPROVAL_INVALIDATED", "la aprobación fue invalidada"
                )
            if entry.state is ApprovalState.EXPIRED:
                raise ApprovalError("APPROVAL_EXPIRED", "la aprobación expiró")
            if self._clock() - entry.created_at_ms > self._ttl_ms:
                entry.state = ApprovalState.EXPIRED
                raise ApprovalError("APPROVAL_EXPIRED", "la aprobación expiró")
            if (
                entry.device_fingerprint != approved.device_fingerprint
                or entry.manifest_digest != approved.manifest_digest
                or entry.provisioning_fingerprint != approved.provisioning_fingerprint
                or entry.mode != approved.plan.mode.value
            ):
                entry.state = ApprovalState.INVALIDATED
                raise ApprovalError(
                    "APPROVAL_INVALIDATED",
                    "la aprobación cambió desde que fue emitida",
                )
            entry.state = ApprovalState.CONSUMED
