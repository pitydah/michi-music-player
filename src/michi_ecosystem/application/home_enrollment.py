"""Home enrollment orchestration (M11) — wire-neutral.

Candidate identity + membership semantics + roster pending state. No v3 JSON,
no canonical signing payload: the issuer arrives through ``MembershipIssuerPort``
(the product issuer waits for the Michi Link v3 freeze).
"""

from __future__ import annotations

from michi_ecosystem.domain.device_confirmation import (
    DeviceConfirmation,
    DeviceConfirmationError,
)
from michi_ecosystem.domain.home import (
    DeviceRole,
    DeviceRosterEntry,
    DomainError,
    HomeMembership,
    MembershipStatus,
    MichiHomeProfile,
)
from michi_ecosystem.infrastructure.michi_link.confirmation import (
    verify_device_confirmation,
)
from michi_ecosystem.ports.device_identity import (
    CandidateDeviceIdentity,
    DeviceIdentityProviderPort,
)
from michi_ecosystem.ports.home import (
    DeviceRosterRepositoryPort,
    MembershipIssuerPort,
)


class EnrollmentError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class HomeEnrollmentService:
    def __init__(
        self,
        *,
        identity_provider: DeviceIdentityProviderPort,
        issuer: MembershipIssuerPort,
        roster: DeviceRosterRepositoryPort,
    ) -> None:
        self._identity_provider = identity_provider
        self._issuer = issuer
        self._roster = roster

    def begin(
        self,
        *,
        home: MichiHomeProfile,
        device_name: str,
        roles: tuple[DeviceRole, ...],
    ) -> tuple[CandidateDeviceIdentity, HomeMembership]:
        """Create a candidate identity + membership; roster entry stays PENDING."""
        identity = self._identity_provider.create_candidate()
        membership = self._issuer.issue(
            home=home,
            device_michi_id=identity.michi_id,
            device_public_key=identity.public_key,
            roles=roles,
        )
        entry = DeviceRosterEntry(
            device_michi_id=identity.michi_id,
            device_name=device_name,
            roles=roles,
            status=MembershipStatus.PENDING,
            membership_serial=membership.serial.value,
        )
        try:
            self._roster.add(entry)
        except DomainError as exc:
            self._identity_provider.abort()
            raise EnrollmentError("DEVICE_REVOKED", str(exc)) from exc
        return identity, membership

    def commit(
        self,
        identity: CandidateDeviceIdentity,
        *,
        confirmation: DeviceConfirmation,
    ) -> None:
        """Activate only with cryptographic proof of the prepared identity.

        Order (C0.2): roster activation first; the provider is finalized only
        after the roster committed. A failed activation leaves the provider
        candidate recoverable (retry or abort), never silently released.
        There is no boolean shortcut: a missing/invalid proof keeps PENDING.
        """
        try:
            verify_device_confirmation(
                confirmation, expected_michi_id=identity.michi_id
            )
        except DeviceConfirmationError as exc:
            raise EnrollmentError(exc.code, exc.message) from exc
        try:
            self._roster.activate(identity.michi_id)
        except DomainError as exc:
            raise EnrollmentError("ENROLLMENT_NOT_ACTIVATABLE", str(exc)) from exc
        self._identity_provider.finalize()

    def abort(self, identity: CandidateDeviceIdentity) -> None:
        """Resolve the pending roster entry AND discard candidate material.

        Policy (C0.1): PENDING becomes ABORTED (audit trail kept, never
        usable) instead of lingering as a ghost pending enrollment; the
        provider candidate is discarded. Idempotent for repeated failures.
        """
        self._roster.abort_pending(identity.michi_id)
        self._identity_provider.abort()
