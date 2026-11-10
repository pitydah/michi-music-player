"""Verification of post-flash device confirmations (I3).

Uses the same canonical primitives as signed discovery: Base64URL decoding,
BLAKE3-derived ``michi_id`` and Ed25519 verification. A confirmation that does
not prove possession of the prepared identity is rejected with a typed code;
nothing is activated on a partial match.
"""

from __future__ import annotations

from michi_ecosystem.domain.device_confirmation import (
    DeviceConfirmation,
    DeviceConfirmationError,
)
from michi_ecosystem.infrastructure.michi_link.verification import (
    b64url_decode,
    derive_michi_id,
    verify_ed25519,
)

MIN_CHALLENGE_BYTES = 16


def verify_device_confirmation(
    confirmation: DeviceConfirmation, *, expected_michi_id: str
) -> None:
    """Raise ``DeviceConfirmationError`` unless every binding matches."""
    if not isinstance(confirmation, DeviceConfirmation):
        raise DeviceConfirmationError(
            "CONFIRMATION_INVALID", "se requiere una confirmación verificable"
        )
    expected = str(expected_michi_id)
    if confirmation.device_michi_id != expected:
        raise DeviceConfirmationError(
            "CONFIRMATION_IDENTITY_MISMATCH",
            "la identidad confirmada no es la identidad preparada",
        )
    if confirmation.observed_michi_id != confirmation.device_michi_id:
        raise DeviceConfirmationError(
            "CONFIRMATION_IDENTITY_MISMATCH",
            "la identidad observada tras el flasheo no coincide",
        )
    if not confirmation.flash_reference:
        raise DeviceConfirmationError(
            "CONFIRMATION_FLASH_REFERENCE_MISSING",
            "la confirmación no referencia el flasheo que la produjo",
        )
    try:
        derived = derive_michi_id(confirmation.public_key)
    except ValueError as exc:
        raise DeviceConfirmationError(
            "CONFIRMATION_INVALID", "clave pública malformada"
        ) from exc
    if derived != confirmation.device_michi_id:
        raise DeviceConfirmationError(
            "CONFIRMATION_IDENTITY_MISMATCH",
            "la clave pública no deriva en el michi_id confirmado",
        )
    try:
        challenge = b64url_decode(confirmation.challenge)
    except ValueError as exc:
        raise DeviceConfirmationError(
            "CONFIRMATION_CHALLENGE_INVALID", "challenge malformado"
        ) from exc
    if len(challenge) < MIN_CHALLENGE_BYTES:
        raise DeviceConfirmationError(
            "CONFIRMATION_CHALLENGE_INVALID", "challenge demasiado corto"
        )
    if not verify_ed25519(
        confirmation.public_key,
        confirmation.challenge_signature,
        challenge,
    ):
        raise DeviceConfirmationError(
            "CONFIRMATION_SIGNATURE_INVALID",
            "la firma del challenge no corresponde a la clave confirmada",
        )
