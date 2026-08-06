"""Integration: MobileSyncService trust revocation + rate limiting (Slice 7).

- A revoked device is reported as revoked in health and loses trust.
- Re-pairing the same device id requires a NEW pairing (old trust is never
  reused); the fingerprint/public key are replaced.
- Rapid pairing attempts are rate-limited (in-memory counters, documented).
"""
from __future__ import annotations

import hashlib
import hmac

import pytest

from library.library_db import LibraryDB


@pytest.fixture
def db(tmp_path) -> LibraryDB:
    return LibraryDB(str(tmp_path / "mobile.db"))


def _proof(code: str, challenge: str) -> str:
    return hmac.new(code.encode(), challenge.encode(),
                    hashlib.sha256).hexdigest()


def _pair_device(svc, device_id: str, public_key: str) -> None:
    pair = svc.start_pairing()
    challenge = svc.get_pairing_challenge(pair["session_id"])["challenge"]
    result = svc.verify_pairing(
        pair["session_id"], pair["code"],
        device_id=device_id, public_key=public_key,
        fingerprint=f"fp-{device_id}",
        proof=_proof(pair["code"], challenge),
    )
    assert result["ok"]


def test_revoked_device_reported_in_health(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    _pair_device(svc, "dev-revoked", "pk-old")

    assert svc.revoke_trust("dev-revoked")["ok"]
    health = svc.health()
    assert health["revoked_devices"] == 1
    assert health["trusted_devices"] == 0
    assert not svc.is_trusted("dev-revoked")

    # Re-pairing the SAME device id requires a NEW pairing session.
    pair = svc.start_pairing()
    challenge = svc.get_pairing_challenge(pair["session_id"])["challenge"]
    re_pair = svc.verify_pairing(
        pair["session_id"], pair["code"],
        device_id="dev-revoked", public_key="pk-new",
        fingerprint="fp-new",
        proof=_proof(pair["code"], challenge),
    )
    assert re_pair["ok"]
    assert svc.is_trusted("dev-revoked")
    info = svc.get_pairing_info("dev-revoked")
    assert info["public_key"] == "pk-new"  # old trust NOT reused
    assert info["fingerprint"] == "fp-new"
    assert info["revoked"] is False


def test_revoked_device_cannot_use_old_trust_without_new_pairing(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    _pair_device(svc, "dev-old", "pk-a")
    svc.revoke_trust("dev-old")
    assert not svc.is_trusted("dev-old")

    # A wrong-code attempt on a fresh session must NOT restore trust.
    pair = svc.start_pairing()
    result = svc.verify_pairing(pair["session_id"], "000000",
                                device_id="dev-old", public_key="pk-a")
    assert not result["ok"]
    assert not svc.is_trusted("dev-old")
    assert svc.get_pairing_info("dev-old")["revoked"] is True


def test_rate_limiting_blocks_rapid_pairing_attempts(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
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


def test_health_listener_state_is_truthful_when_not_running(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    health = svc.health()
    # No listener started → server_listening MUST be False (never assumed).
    assert health["server_listening"] is False
    assert health["server_configured"] is True
    assert health["tls_available"] is False
