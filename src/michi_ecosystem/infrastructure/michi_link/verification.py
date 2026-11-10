"""Canonical Michi Link verification for receiver-v1-lite payloads.

Implements the signed-announce pipeline and pairing challenge checks defined by
``docs/DISCOVERY.md`` ("Signed Announce Verification") and ``docs/PAIRING.md``,
mirroring the protocol's canonical serialization (lexicographic JSON over the
present functional announce fields; the signature is never part of the signed
bytes). Correctness is pinned by the vendored golden vectors from
``michi-link`` (master plan §155.1).

Phase: E2 (validators + trust projection).
"""

from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import math
import re
from collections.abc import Mapping, MutableSet
from typing import Any

import blake3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from michi_ecosystem.domain.trust import AnnounceVerification, TrustLevel

TIMESTAMP_WINDOW_MS = 90_000

IDENTITY_FIELDS = ("michi_id", "public_key", "signature", "timestamp_ms", "nonce")

CANONICAL_FIELDS = (
    "api_version",
    "device_id",
    "features",
    "host",
    "membership_fingerprint",
    "michi_home_id",
    "michi_id",
    "name",
    "nonce",
    "port",
    "public_key",
    "roles",
    "service",
    "timestamp_ms",
)

REASON_SIGNATURE_INVALID = "signature_invalid"
REASON_IDENTITY_MISMATCH = "identity_mismatch"
REASON_TIMESTAMP_OUT_OF_WINDOW = "timestamp_out_of_window"
REASON_REPLAY_DETECTED = "replay_detected"
REASON_HOST_MISMATCH = "host_mismatch"
REASON_PARTIAL_IDENTITY_GROUP = "partial_identity_group"
REASON_UNSIGNED = "unsigned"
REASON_VERIFIED = "verified"


def b64url_decode(value: str) -> bytes:
    """Reject malformed Base64URL as ValueError at the untrusted UDP boundary.

    urlsafe_b64decode silently discards some punctuation and raises
    binascii.Error for other malformed strings; neither is acceptable for a
    signed Michi Link announce. Padding remains optional by contract.
    """
    if (
        not isinstance(value, str)
        or not value
        or re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", value) is None
    ):
        raise ValueError("invalid base64url characters")
    if len(value.rstrip("=")) % 4 == 1:
        raise ValueError("invalid base64url length")
    try:
        return base64.b64decode(
            value.rstrip("=") + "=" * (-len(value.rstrip("=")) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ValueError("invalid base64url encoding") from exc


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def derive_michi_id(public_key_b64url: str) -> str:
    """michi_id = base64url(BLAKE3(public key raw bytes)), 43 chars (spec)."""
    return b64url_encode(blake3.blake3(b64url_decode(public_key_b64url)).digest())


def canonical_announce_bytes(announce: Mapping[str, Any]) -> bytes:
    """Deterministic canonical serialization of the functional announce fields.

    Lexicographic key order, compact separators, UTF-8 without ASCII escapes —
    mirrors the protocol specification and its golden vectors.
    """
    subset = {key: announce[key] for key in CANONICAL_FIELDS if key in announce}
    return json.dumps(
        subset, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def verify_ed25519(
    public_key_b64url: str, signature_b64url: str, message: bytes
) -> bool:
    """Verify an Ed25519 signature; malformed inputs are simply invalid."""
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            b64url_decode(public_key_b64url)
        )
        public_key.verify(b64url_decode(signature_b64url), message)
    except (InvalidSignature, ValueError):
        return False
    return True


def verify_announce_signature(announce: Mapping[str, Any]) -> bool:
    """Ed25519 signature over the canonical bytes (no signature field)."""
    try:
        return verify_ed25519(
            str(announce["public_key"]),
            str(announce["signature"]),
            canonical_announce_bytes(announce),
        )
    except KeyError:
        return False


def identity_coherent(document: Mapping[str, Any]) -> bool:
    """``michi_id`` must equal the BLAKE3 derivation of the announced key."""
    try:
        return derive_michi_id(str(document["public_key"])) == str(document["michi_id"])
    except (KeyError, ValueError):
        return False


def verify_pair_start_challenge(request: Mapping[str, Any]) -> bool:
    """Ed25519 challenge over the raw nonce bytes (docs/PAIRING.md)."""
    try:
        nonce = b64url_decode(str(request["challenge_nonce"]))
        if len(nonce) < 16:
            return False
        return verify_ed25519(
            str(request["public_key"]),
            str(request["challenge_signature"]),
            nonce,
        )
    except (KeyError, ValueError):
        return False


def nonce_key(announce: Mapping[str, Any]) -> tuple[str, str]:
    """Replay-cache key: (michi_id, nonce)."""
    return (str(announce.get("michi_id", "")), str(announce.get("nonce", "")))


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def verify_announce(
    announce: Mapping[str, Any],
    *,
    now_ms: int | None = None,
    seen_nonces: MutableSet[tuple[str, str]] | None = None,
    source_host: str | None = None,
) -> AnnounceVerification:
    """Signed-announce verification pipeline (docs/DISCOVERY.md).

    Order: signature → identity coherence → freshness → replay → host coherence,
    with the partial-group and unsigned cases decided first. Freshness and
    replay failures are reported as INVALID with a specific reason (fail closed).
    """
    device_id = str(announce.get("device_id", ""))

    present = [field for field in IDENTITY_FIELDS if field in announce]
    if present and len(present) != len(IDENTITY_FIELDS):
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, None, REASON_PARTIAL_IDENTITY_GROUP
        )
    if not present:
        return AnnounceVerification(
            TrustLevel.UNTRUSTED, device_id, None, REASON_UNSIGNED
        )

    michi_id = str(announce.get("michi_id", ""))
    if not verify_announce_signature(announce):
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_SIGNATURE_INVALID
        )
    if not identity_coherent(announce):
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_IDENTITY_MISMATCH
        )

    timestamp = announce.get("timestamp_ms")
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
        or (isinstance(timestamp, float) and not math.isfinite(timestamp))
    ):
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_TIMESTAMP_OUT_OF_WINDOW
        )
    if now_ms is not None and abs(now_ms - int(timestamp)) > TIMESTAMP_WINDOW_MS:
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_TIMESTAMP_OUT_OF_WINDOW
        )

    if seen_nonces is not None and nonce_key(announce) in seen_nonces:
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_REPLAY_DETECTED
        )

    host = str(announce.get("host", ""))
    if source_host and _is_ip(host) and host != source_host:
        return AnnounceVerification(
            TrustLevel.INVALID, device_id, michi_id, REASON_HOST_MISMATCH
        )

    return AnnounceVerification(
        TrustLevel.VERIFIED, device_id, michi_id, REASON_VERIFIED
    )
