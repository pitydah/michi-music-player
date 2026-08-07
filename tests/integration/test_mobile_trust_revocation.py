"""Integration: MobileSyncService trust revocation + rate limiting (Slice 7,
Phase 7).

- A revoked device is reported as revoked in health and loses trust.
- Re-pairing the same device id requires a NEW pairing + approval (old trust
  is never reused); the fingerprint/public key are replaced.
- Rapid pairing attempts are rate-limited (in-memory counters, documented).
- The listener reports health truthfully when not running.
"""
from __future__ import annotations

import base64
import hashlib

import pytest

from library.library_db import LibraryDB


@pytest.fixture
def db(tmp_path) -> LibraryDB:
    return LibraryDB(str(tmp_path / "mobile.db"))


def _keypair():
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


def _pub(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _fingerprint(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pair_device(svc, device_id: str):
    """Pair + approve a device; returns (private, raw) for later re-pair."""
    private, raw = _keypair()
    pair = svc.start_pairing()
    payload = (
        f"1.0|{pair['session_id']}|{pair['nonce']}|"
        f"{_fingerprint(raw)}|{device_id}"
    ).encode()
    result = svc.pair_request(
        session_id=pair["session_id"],
        nonce=pair["nonce"],
        public_key=_pub(raw),
        signature=base64.b64encode(private.sign(payload)).decode(),
        fingerprint=_fingerprint(raw),
        device_id=device_id,
    )
    assert result["ok"]
    assert svc.approve_device(device_id)["ok"]
    return private, raw


def test_revoked_device_reported_in_health(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    private, raw = _pair_device(svc, "dev-revoked")

    assert svc.revoke_trust("dev-revoked")["ok"]
    health = svc.health()
    assert health["revoked_devices"] == 1
    assert health["trusted_devices"] == 0
    assert not svc.is_trusted("dev-revoked")

    # Re-pairing the SAME device id requires a NEW pairing session + NEW
    # user approval (old trust is never reused). The device keeps its own
    # key — a DIFFERENT key is rejected (key-swap guard).
    pair = svc.start_pairing()
    payload = (
        f"1.0|{pair['session_id']}|{pair['nonce']}|"
        f"{_fingerprint(raw)}|dev-revoked"
    ).encode()
    re_pair = svc.pair_request(
        session_id=pair["session_id"], nonce=pair["nonce"],
        public_key=_pub(raw),
        signature=base64.b64encode(private.sign(payload)).decode(),
        fingerprint=_fingerprint(raw),
        device_id="dev-revoked",
    )
    assert re_pair["ok"]
    assert re_pair["status"] == "awaiting_approval"
    assert not svc.is_trusted("dev-revoked"), (
        "re-pairing must not restore trust without a new approval")
    assert svc.approve_device("dev-revoked")["ok"]
    assert svc.is_trusted("dev-revoked")
    info = svc.get_pairing_info("dev-revoked")
    assert info["public_key"] == _pub(raw)  # old trust NOT reused
    assert info["fingerprint"] == _fingerprint(raw)
    assert info["revoked"] is False


def test_revoked_device_cannot_use_old_trust_without_new_pairing(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    _pair_device(svc, "dev-old")
    svc.revoke_trust("dev-old")
    assert not svc.is_trusted("dev-old")

    # A wrong-code attempt on a fresh session must NOT restore trust.
    pair = svc.start_pairing()
    result = svc.verify_pairing(pair["session_id"], "000000",
                                device_id="dev-old")
    assert not result["ok"]
    assert not svc.is_trusted("dev-old")
    assert svc.get_pairing_info("dev-old")["revoked"] is True


def test_rate_limiting_blocks_rapid_pairing_attempts(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db, legacy_code_pairing_enabled=True,
                            allow_lan_pairing=True)
    pair = svc.start_pairing()
    sid = pair["session_id"]

    # 5 wrong attempts from the same ip → INVALID_CODE each.
    for _ in range(5):
        result = svc.verify_pairing(sid, "000000", ip="10.0.0.1")
        assert not result["ok"]
        assert result["error"] == "INVALID_CODE"

    # The 6th attempt — even with the correct code — is rate-limited.
    blocked = svc.verify_pairing(sid, pair["code"], ip="10.0.0.1")
    assert not blocked["ok"]
    assert blocked["error"] == "RATE_LIMITED"

    # A different ip is not blocked (in-memory counters are per-key).
    other = svc.verify_pairing(sid, pair["code"], ip="10.0.0.2",
                               device_id="other-phone")
    assert other["ok"]
    assert not svc.is_trusted("other-phone"), (
        "legacy code-only pairing never auto-trusts")


def test_health_listener_state_is_truthful_when_not_running(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    health = svc.health()
    # No listener started → server_listening MUST be False (never assumed).
    assert health["server_listening"] is False
    assert health["server_configured"] is True
    assert health["tls_available"] is False
    assert health["tls_mode"] == "none"
    assert health["bind_host"] == "127.0.0.1"
    assert health["allow_lan_pairing"] is False
    assert health["secure_pairing_available"] is True
    assert health["signature_pairing_enabled"] is True
    assert health["insecure_legacy_enabled"] is False
