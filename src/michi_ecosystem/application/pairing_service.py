"""Pairing application service (E7): capability-driven flows and recovery.

Wraps the Micro Server receiver pairing endpoints
(``POST /api/v1/receivers/pair/start`` and ``/pair/confirm``) with the
canonical strategy requirements from ``docs/PAIRING.md`` and
``pair-start.schema.json``. Transactions stay recoverable: pending receivers
are listed for recovery and re-pairing is always explicit.
"""

from __future__ import annotations

from michi_ecosystem.domain.servers import ReceiverSummary
from michi_ecosystem.domain.trust import (
    PairingConfirmation,
    PairingRequirements,
    PairingStart,
    requirements_for,
)
from michi_ecosystem.ports.micro_server import (
    MicroServerPort,
    MicroServerRequestError,
)


class PairingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class PairingService:
    def __init__(self, micro: MicroServerPort) -> None:
        self._micro = micro

    @staticmethod
    def requirements_for(strategy: str) -> PairingRequirements:
        try:
            return requirements_for(strategy)
        except ValueError as exc:
            raise PairingError("UNKNOWN_STRATEGY", str(exc)) from exc

    def begin(
        self,
        *,
        receiver_id: str | None = None,
        base_url: str | None = None,
        re_pair: bool = False,
    ) -> PairingStart:
        """Open a pairing transaction (PIN displayed by the receiver)."""
        if not receiver_id and not base_url:
            raise PairingError("INVALID_REQUEST", "receiver_id or base_url is required")
        try:
            return self._micro.start_receiver_pairing(
                receiver_id=receiver_id, base_url=base_url, re_pair=re_pair
            )
        except MicroServerRequestError as exc:
            raise PairingError(exc.code, exc.message) from exc

    def confirm(
        self,
        *,
        pin: str,
        pairing_id: str | None = None,
        receiver_id: str | None = None,
    ) -> PairingConfirmation:
        """Confirm the transaction with the receiver-displayed PIN."""
        if not pin:
            raise PairingError("INVALID_REQUEST", "pin is required")
        if not pairing_id and not receiver_id:
            raise PairingError(
                "INVALID_REQUEST", "pairing_id or receiver_id is required"
            )
        try:
            return self._micro.confirm_receiver_pairing(
                pin=pin, pairing_id=pairing_id, receiver_id=receiver_id
            )
        except MicroServerRequestError as exc:
            raise PairingError(exc.code, exc.message) from exc

    def recovery_candidates(
        self, receivers: tuple[ReceiverSummary, ...]
    ) -> tuple[ReceiverSummary, ...]:
        """Receivers needing pairing or trust completion (transaction recovery)."""
        return tuple(receiver for receiver in receivers if receiver.pairing_pending)
