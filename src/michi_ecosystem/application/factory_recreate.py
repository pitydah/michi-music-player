"""Factory Recreate transaction service (M14 + C0.4/C0.5/C0.7).

Life cycle: CREATED -> REPLACEMENT_PENDING -> FLASHING -> FLASH_VERIFIED ->
COMMITTED. The old identity is never revoked before the flash succeeded and
the device confirmed. Crash handling is deterministic:

- CREATED/REPLACEMENT_PENDING: rolled back to ACTIVE (write-ahead record).
- FLASHING: parked as RECOVERY_REQUIRED — never silently resolved.
- FLASH_VERIFIED: committable after device confirmation (with forward
  reconciliation if the crash happened between finalize and state write).
"""

from __future__ import annotations

import contextlib

from michi_ecosystem.domain.home import DomainError, MembershipStatus
from michi_ecosystem.infrastructure.home.recreate_transaction import (
    FactoryRecreateStore,
    RecreateState,
)
from michi_ecosystem.ports.home import DeviceRosterRepositoryPort


class RecreateError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class FactoryRecreateService:
    def __init__(
        self,
        *,
        store: FactoryRecreateStore,
        roster: DeviceRosterRepositoryPort,
    ) -> None:
        self._store = store
        self._roster = roster

    # ── lifecycle ───────────────────────────────────────────────────────

    def begin(
        self,
        *,
        old_device_id: str,
        candidate_michi_id: str,
        candidate_serial: str,
    ) -> str:
        """Write-ahead first (C0.4): a persisted transaction always exists."""
        tx_id = self._store.create(
            old_device_id=old_device_id,
            candidate_michi_id=candidate_michi_id,
            candidate_serial=candidate_serial,
        )
        try:
            self._roster.mark_replacement_pending(old_device_id, candidate_serial)
        except DomainError as exc:
            self._store.set_state(tx_id, RecreateState.FAILED, str(exc))
            raise RecreateError("REPLACEMENT_NOT_STARTED", str(exc)) from exc
        self._store.set_state(tx_id, RecreateState.REPLACEMENT_PENDING)
        return tx_id

    def mark_flashing(self, tx_id: str) -> None:
        self._require_state(tx_id, RecreateState.REPLACEMENT_PENDING)
        self._store.set_state(tx_id, RecreateState.FLASHING)

    def mark_flash_verified(self, tx_id: str) -> None:
        self._require_state(tx_id, RecreateState.FLASHING)
        self._store.set_state(tx_id, RecreateState.FLASH_VERIFIED)

    def record_flash_success(self, tx_id: str) -> None:
        """Idempotent transition to FLASH_VERIFIED (covers a missed hook)."""
        transaction = self._store.get(tx_id)
        if transaction.state is RecreateState.FLASH_VERIFIED:
            return
        if transaction.state is RecreateState.REPLACEMENT_PENDING:
            self._store.set_state(tx_id, RecreateState.FLASHING)
            transaction = self._store.get(tx_id)
        if transaction.state is RecreateState.FLASHING:
            self._store.set_state(tx_id, RecreateState.FLASH_VERIFIED)
            return
        raise RecreateError(
            "INVALID_STATE",
            f"no se puede registrar un flash exitoso desde {transaction.state}",
        )

    def commit(self, tx_id: str, *, device_confirmed: bool) -> None:
        transaction = self._store.get(tx_id)
        if transaction.state is RecreateState.COMMITTED:
            return  # idempotent: repeated commit is safe
        if transaction.state is RecreateState.RECOVERY_REQUIRED:
            raise RecreateError(
                "RECOVERY_REQUIRED",
                "el crash ocurrió durante el flasheo; requiere resolución explícita",
            )
        if transaction.state is not RecreateState.FLASH_VERIFIED:
            raise RecreateError(
                "INVALID_STATE", f"no se puede commitear desde {transaction.state}"
            )
        if not device_confirmed:
            raise RecreateError(
                "DEVICE_CONFIRMATION_REQUIRED",
                "el reemplazo queda pendiente de confirmación del dispositivo",
            )
        self._finalize(transaction, detail="committed")

    def resolve_recovery(
        self,
        tx_id: str,
        *,
        flash_succeeded: bool,
        device_confirmed: bool,
    ) -> None:
        """Explicit operator decision after a crash during FLASHING (C0.7)."""
        transaction = self._store.get(tx_id)
        if transaction.state is not RecreateState.RECOVERY_REQUIRED:
            raise RecreateError(
                "INVALID_STATE",
                "recovery resolution requires RECOVERY_REQUIRED "
                f"(state={transaction.state})",
            )
        if flash_succeeded and device_confirmed:
            self._finalize(transaction, detail="recovery resolution: succeeded")
            return
        self._rollback(transaction)
        self._store.set_state(
            tx_id, RecreateState.ABORTED, "recovery resolution: failed"
        )

    def abort(self, tx_id: str, reason: str = "") -> None:
        transaction = self._store.get(tx_id)
        if transaction.state in TERMINAL_STATES_FOR_ABORT:
            return  # idempotent; never rolls back a committed replacement
        self._rollback(transaction)
        self._store.set_state(tx_id, RecreateState.ABORTED, reason or "aborted")

    # ── crash recovery ──────────────────────────────────────────────────

    def recover(self) -> tuple[str, ...]:
        """Deterministic, idempotent recovery for every open state (C0.7)."""
        resolved: list[str] = []
        for transaction in self._store.open_transactions():
            if transaction.state in (
                RecreateState.CREATED,
                RecreateState.REPLACEMENT_PENDING,
            ):
                self._rollback(transaction)
                self._store.set_state(
                    transaction.tx_id, RecreateState.ABORTED, "crash recovery"
                )
                resolved.append(f"{transaction.tx_id}:ABORTED")
            elif transaction.state is RecreateState.FLASHING:
                # Hardware result unknown: never assume a clean failure.
                self._store.set_state(
                    transaction.tx_id,
                    RecreateState.RECOVERY_REQUIRED,
                    "crash during flash: hardware result unknown",
                )
                resolved.append(f"{transaction.tx_id}:RECOVERY_REQUIRED")
            elif transaction.state is RecreateState.FLASH_VERIFIED:
                if self._roster_finalized(transaction):
                    self._store.set_state(
                        transaction.tx_id,
                        RecreateState.COMMITTED,
                        "reconciled after crash",
                    )
                    resolved.append(f"{transaction.tx_id}:RECONCILED_COMMITTED")
                else:
                    resolved.append(f"{transaction.tx_id}:COMMITTABLE")
            elif transaction.state is RecreateState.RECOVERY_REQUIRED:
                resolved.append(f"{transaction.tx_id}:AWAITING_RESOLUTION")
        return tuple(resolved)

    # ── internals ───────────────────────────────────────────────────────

    def _finalize(self, transaction, *, detail: str) -> None:
        if not self._roster_finalized(transaction):
            try:
                self._roster.finalize_replacement(
                    transaction.old_device_id, transaction.candidate_michi_id
                )
            except DomainError as exc:
                raise RecreateError("REPLACEMENT_FAILED", str(exc)) from exc
        self._store.set_state(transaction.tx_id, RecreateState.COMMITTED, detail)

    def _roster_finalized(self, transaction) -> bool:
        old = self._roster.get(transaction.old_device_id)
        new = self._roster.get(transaction.candidate_michi_id)
        return (
            old is not None
            and new is not None
            and old.status is MembershipStatus.REPLACED
            and new.status is MembershipStatus.ACTIVE
        )

    def _rollback(self, transaction) -> None:
        # Idempotent in the roster: no-op unless still REPLACEMENT_PENDING.
        self._roster.rollback_replacement(transaction.old_device_id)
        # B1: the candidate must never linger as a usable PENDING entry when
        # the recreate is definitively aborted (abort / crash recovery /
        # failed recovery resolution). ABORTED keeps the audit trail.
        with contextlib.suppress(DomainError):
            self._roster.abort_pending(transaction.candidate_michi_id)

    def _require_state(self, tx_id: str, expected: RecreateState) -> None:
        transaction = self._store.get(tx_id)
        if transaction.state is not expected:
            raise RecreateError(
                "INVALID_STATE",
                f"esperaba {expected}, encontré {transaction.state}",
            )


TERMINAL_STATES_FOR_ABORT = frozenset(
    {
        RecreateState.COMMITTED,
        RecreateState.ABORTED,
        RecreateState.FAILED,
    }
)
