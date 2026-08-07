"""Integration: MobileSyncService challenge-response signature pairing (Phase 7).

The HMAC-of-6-digit-code pairing is replaced by a REAL public-key proof:

- Server issues session_id + one-time nonce.
- Device signs ``protocol_version|session_id|nonce|fingerprint|device_id``
  with its Ed25519 private key.
- Server verifies the signature, derives the fingerprint from the public
  key material (never trusting a client-supplied one), creates the device
  as ``awaiting_approval``, and only ``approve_device()`` makes it trusted
  (persisted).
- Legacy code-only pairing is disabled by default; when enabled it is
  loopback-restricted (unless allow_lan_pairing), never auto-trusted,
  TTL-bounded and audit-flagged.
"""
from __future__ import annotations

import base64
import hashlib
from unittest.mock import patch

import pytest

from library.library_db import LibraryDB


@pytest.fixture
def db(tmp_path) -> LibraryDB:
    return LibraryDB(str(tmp_path / "mobile.db"))


def _ed25519_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PublicFormat,
    )

    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private, raw


def _public_key_b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _fingerprint(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sign(private, payload: bytes) -> str:
    return base64.b64encode(private.sign(payload)).decode()


def _signature_payload(protocol_version: str, session_id: str, nonce: str,
                       fingerprint: str, device_id: str) -> bytes:
    return (
        f"{protocol_version}|{session_id}|{nonce}|{fingerprint}|{device_id}"
    ).encode()


def _start_session(svc) -> dict:
    pair = svc.start_pairing()
    assert pair["ok"]
    assert pair["nonce"], "start_pairing must issue a nonce"
    return pair


def _signed_request(svc, private, raw_key, device_id: str = "phone-1",
                    name: str = "Phone 1", fingerprint: str | None = None,
                    protocol_version: str = "1.0") -> dict:
    pair = _start_session(svc)
    fp = fingerprint if fingerprint is not None else _fingerprint(raw_key)
    payload = _signature_payload(protocol_version, pair["session_id"],
                                 pair["nonce"], fp, device_id)
    return {
        "session_id": pair["session_id"],
        "nonce": pair["nonce"],
        "public_key": _public_key_b64(raw_key),
        "signature": _sign(private, payload),
        "fingerprint": fp,
        "device_id": device_id,
        "name": name,
        "protocol_version": protocol_version,
    }


def test_valid_signature_pairing(db) -> None:
    """Server issues session+nonce → device signs → approve → trusted,
    and the trusted device survives a restart."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc1 = MobileSyncService(db=db)
    req = _signed_request(svc1, private, raw, device_id="phone-a",
                          name="Phone A")

    result = svc1.pair_request(**req)
    assert result["ok"]
    assert result["status"] == "awaiting_approval"
    assert result["fingerprint"] == _fingerprint(raw)
    assert not svc1.is_trusted("phone-a"), (
        "signature pairing must NOT auto-trust: approval is required")

    # Client-provided fingerprint is only compared; the stored one is
    # derived server-side from the public key material.
    info = svc1.get_pairing_info("phone-a")
    assert info["fingerprint"] == _fingerprint(raw)

    assert svc1.approve_device("phone-a")["ok"]
    assert svc1.is_trusted("phone-a")

    # Restart: the trusted device survives with the derived fingerprint.
    svc2 = MobileSyncService(db=db)
    assert svc2.is_paired("phone-a")
    assert svc2.is_trusted("phone-a")
    info2 = svc2.get_pairing_info("phone-a")
    assert info2["fingerprint"] == _fingerprint(raw)
    assert info2["status"] == "trusted"

    row = db.conn.execute(
        "SELECT public_key, fingerprint, trusted, revoked "
        "FROM mobile_sync_devices WHERE device_id='phone-a'"
    ).fetchone()
    assert row is not None
    assert row[1] == _fingerprint(raw)
    assert row[2] == 1
    assert row[3] == 0


def test_invalid_signature_rejected(db) -> None:
    """Garbage/forged signature → SIGNATURE_INVALID, no device created."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    req = _signed_request(svc, private, raw, device_id="phone-b")
    req["signature"] = base64.b64encode(b"x" * 64).decode()

    result = svc.pair_request(**req)
    assert not result["ok"]
    assert result["error"] == "SIGNATURE_INVALID"
    assert not svc.is_paired("phone-b")

    # A signature over a DIFFERENT payload (device_id swapped) also fails.
    svc2 = MobileSyncService(db=db)
    req2 = _signed_request(svc2, private, raw, device_id="phone-b")
    forged = _signature_payload("1.0", req2["session_id"], req2["nonce"],
                                _fingerprint(raw), "phone-CORRUPT")
    req2["signature"] = _sign(private, forged)
    result2 = svc2.pair_request(**req2)
    assert not result2["ok"]
    assert result2["error"] == "SIGNATURE_INVALID"


def test_wrong_key_rejected(db) -> None:
    """Signature by a DIFFERENT key than the presented public key fails."""
    from core.mobile_sync_service import MobileSyncService

    signer_private, _ = _ed25519_keypair()
    _, victim_raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    req = _signed_request(svc, signer_private, victim_raw, device_id="phone-c")

    result = svc.pair_request(**req)
    assert not result["ok"]
    assert result["error"] == "SIGNATURE_INVALID"
    assert not svc.is_paired("phone-c")


def test_nonce_replay_rejected(db) -> None:
    """The nonce is single-use: a second request reusing it → NONCE_REUSED."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    req = _signed_request(svc, private, raw, device_id="phone-d")

    first = svc.pair_request(**req)
    assert first["ok"]
    assert svc.is_paired("phone-d")

    second = svc.pair_request(**req)
    assert not second["ok"]
    assert second["error"] == "NONCE_REUSED"


def test_session_expired(db) -> None:
    """Expired session → SESSION_EXPIRED (no signature accepted)."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    with patch("time.time", return_value=1000):
        pair = svc.start_pairing()
    payload = _signature_payload("1.0", pair["session_id"], pair["nonce"],
                                 _fingerprint(raw), "phone-e")
    req = {
        "session_id": pair["session_id"], "nonce": pair["nonce"],
        "public_key": _public_key_b64(raw),
        "signature": _sign(private, payload),
        "device_id": "phone-e",
    }
    with patch("time.time", return_value=2000):
        result = svc.pair_request(**req)
    assert not result["ok"]
    assert result["error"] == "SESSION_EXPIRED"


def test_code_without_signature_fails(db) -> None:
    """Code-only pairing without a signature is rejected by default."""
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    pair = _start_session(svc)
    result = svc.verify_pairing(pair["session_id"], pair["code"],
                                device_id="legacy-1")
    assert not result["ok"]
    assert result["error"] == "SIGNATURE_REQUIRED"
    assert not svc.is_paired("legacy-1")


def test_legacy_mode_flagged(db) -> None:
    """Legacy enabled → code-only device awaits approval, is NOT trusted,
    TTL is bounded, an audit entry exists and health flags it as insecure."""
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db, legacy_code_pairing_enabled=True)
    pair = svc.start_pairing()
    session = svc.get_pending_sessions()[0]
    assert session["expires_at"] - session["created_at"] == 300, (
        "pairing sessions must be TTL-bounded (5 minutes)")
    result = svc.verify_pairing(pair["session_id"], pair["code"],
                                device_id="legacy-2", ip="127.0.0.1")
    assert result["ok"]
    assert result["status"] == "awaiting_approval"
    assert not svc.is_trusted("legacy-2"), (
        "legacy code-only pairing must NEVER auto-trust")

    # TTL: legacy sessions expire after the documented 5 minutes.
    from core.mobile_sync_service import _LEGACY_TTL
    assert _LEGACY_TTL == 300
    assert svc.health()["legacy_ttl_seconds"] == 300

    # Audit entry kind.
    kinds = [e["kind"] for e in svc.get_audit_entries()]
    assert "legacy_code_pairing" in kinds

    # Health flags.
    health = svc.health()
    assert health["insecure_legacy_enabled"] is True
    assert health["signature_pairing_enabled"] is True
    assert health["secure_pairing_available"] is True

    # Manual approval is still required to grant trust.
    assert svc.approve_device("legacy-2")["ok"]
    assert svc.is_trusted("legacy-2")


def test_persistence_failure_invalidates(db, monkeypatch) -> None:
    """DB write failure → PERSISTENCE_FAILED; device never trusted in memory."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    req = _signed_request(svc, private, raw, device_id="phone-f")

    monkeypatch.setattr(svc, "_persist_device", lambda _device: False)
    result = svc.pair_request(**req)
    assert not result["ok"]
    assert result["error"] == "PERSISTENCE_FAILED"
    assert not svc.is_paired("phone-f"), (
        "a device that failed to persist must not stay in memory")
    assert not svc.is_trusted("phone-f")


def test_revocation_persisted(db) -> None:
    """Revoke → survives restart (device no longer trusted)."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc1 = MobileSyncService(db=db)
    req = _signed_request(svc1, private, raw, device_id="phone-g")
    assert svc1.pair_request(**req)["ok"]
    assert svc1.approve_device("phone-g")["ok"]
    assert svc1.revoke_trust("phone-g")["ok"]

    svc2 = MobileSyncService(db=db)
    assert svc2.is_paired("phone-g")
    assert not svc2.is_trusted("phone-g")
    assert svc2.get_pairing_info("phone-g")["revoked"] is True


def test_device_registry_injected_single(db, tmp_path) -> None:
    """The service uses the injected canonical registry — no duplicate."""
    from core.mobile_sync_service import MobileSyncService
    from core.sync.device_registry import DeviceRegistry

    registry = DeviceRegistry(
        path=str(tmp_path / "paired_devices.json"))
    svc = MobileSyncService(db=db, device_registry=registry, port=0)
    assert svc._device_registry is registry

    result = svc.start()
    try:
        assert result["ok"], result
        assert svc._listener is not None
        assert svc._listener._device_registry is registry, (
            "listener must receive the injected registry, not a new one")
        assert svc._device_registry is registry
        assert svc.is_listening()
    finally:
        svc.stop()


def test_bind_restricted(db) -> None:
    """Loopback bind: pairing from an external source → NETWORK_DENIED.
    Explicit LAN policy (allow_lan_pairing + allowed_networks) permits it."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)  # default: bind_host 127.0.0.1
    req = _signed_request(svc, private, raw, device_id="phone-h")
    denied = svc.pair_request(**{**req, "ip": "192.168.1.50"})
    assert not denied["ok"]
    assert denied["error"] == "NETWORK_DENIED"

    # Same request through verify_pairing is also network-gated.
    pair = _start_session(svc)
    code_denied = svc.verify_pairing(
        pair["session_id"], pair["code"], ip="192.168.1.50")
    assert not code_denied["ok"]
    assert code_denied["error"] == "NETWORK_DENIED"

    # Explicit policy: LAN allowed within the configured CIDR.
    lan = MobileSyncService(db=db, allow_lan_pairing=True,
                            allowed_networks=["192.168.1.0/24"])
    req2 = _signed_request(lan, private, raw, device_id="phone-h")
    allowed = lan.pair_request(**{**req2, "ip": "192.168.1.50"})
    assert allowed["ok"]
    assert allowed["status"] == "awaiting_approval"

    # And a source OUTSIDE the allowed networks is still denied.
    denied2 = lan.pair_request(**{**req2, "ip": "10.0.0.9"})
    assert not denied2["ok"]
    assert denied2["error"] == "NETWORK_DENIED"


def test_fingerprint_mismatch_rejected(db) -> None:
    """A client-chosen fingerprint that does not match its own key is
    rejected: the fingerprint is derived server-side."""
    from core.mobile_sync_service import MobileSyncService

    private, raw = _ed25519_keypair()
    svc = MobileSyncService(db=db)
    req = _signed_request(svc, private, raw, device_id="phone-i",
                          fingerprint="deadbeef" * 8)
    result = svc.pair_request(**req)
    assert not result["ok"]
    assert result["error"] == "FINGERPRINT_MISMATCH"
    assert not svc.is_paired("phone-i")


def test_routes_not_mounted(db, monkeypatch) -> None:
    """Unmounted Michi Link routes → listener not operational."""
    from core.mobile_sync_service import MobileSyncService
    from sync.sync_server import SyncRequestHandler

    monkeypatch.setattr(
        "integrations.michi_link.server.MichiLinkServer.mount",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(SyncRequestHandler, "_michi_link_mounted", False)

    svc = MobileSyncService(db=db)
    result = svc.start()
    assert not result["ok"]
    assert result["error"] == "ROUTES_NOT_MOUNTED"
    assert result.get("listening") is False
    assert not svc.is_listening()
    assert svc.health()["routes_mounted"] is False
    assert svc.health()["server_listening"] is False


def test_key_swap_pending_device_rejected(db) -> None:
    """A second device claiming the SAME pending device_id with a DIFFERENT
    public key must be rejected (DEVICE_ID_CONFLICT) — the pending identity
    cannot be swapped before user approval."""
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)

    # Attacker claims device_id "phone-x" with attacker's own key first.
    atk_private, atk_raw = _ed25519_keypair()
    req1 = _signed_request(svc, atk_private, atk_raw, device_id="phone-x",
                           name="Attacker")
    result1 = svc.pair_request(**req1)
    assert result1["ok"]
    assert result1["status"] == "awaiting_approval"

    # Victim tries the same device_id with a different key → conflict.
    vic_private, vic_raw = _ed25519_keypair()
    req2 = _signed_request(svc, vic_private, vic_raw, device_id="phone-x",
                           name="Victim")
    result2 = svc.pair_request(**req2)
    assert not result2["ok"]
    assert result2["error"] == "DEVICE_ID_CONFLICT"

    # The pending device still holds the FIRST key (not swapped).
    pending = svc._paired_devices.get("phone-x")
    assert pending is not None
    assert pending.public_key == _public_key_b64(atk_raw)

    # The same key can still re-request (idempotent, no conflict).
    req3 = _signed_request(svc, atk_private, atk_raw, device_id="phone-x",
                           name="Attacker")
    result3 = svc.pair_request(**req3)
    assert result3["ok"]
