"""Integration: MobileSyncService persistent pairing (Slice 7, Phase 7).

Pairing/trust/revocation survive service restarts through the
``mobile_sync_devices`` table (migration 8). Since Phase 7 the proof of
possession is a REAL Ed25519 signature (challenge-response), the fingerprint
is derived server-side, and code-only pairing is a disabled-by-default,
never-auto-trusted legacy mode.
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


def _pair_device(svc, device_id: str) -> None:
    """Full secure flow: signature pairing + explicit user approval."""
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
        name=f"Device {device_id}",
    )
    assert result["ok"], result
    assert svc.approve_device(device_id)["ok"]


def test_pairing_survives_restart(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc1 = MobileSyncService(db=db)
    _pair_device(svc1, "phone-a")

    # New instance, same DB: the device is still paired and trusted.
    svc2 = MobileSyncService(db=db)
    assert svc2.is_paired("phone-a")
    assert svc2.is_trusted("phone-a")
    info = svc2.get_pairing_info("phone-a")
    assert info is not None
    assert info["name"] == "Device phone-a"
    assert info["public_key"]
    assert info["fingerprint"]
    assert info["trusted"] is True

    # And the DB row exists with the device identity columns.
    row = db.conn.execute(
        "SELECT device_id, name, public_key, fingerprint, trusted, revoked "
        "FROM mobile_sync_devices WHERE device_id='phone-a'"
    ).fetchone()
    assert row is not None
    assert row[2] == info["public_key"]
    assert row[3] == info["fingerprint"]
    assert row[4] == 1


def test_revocation_survives_restart(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc1 = MobileSyncService(db=db)
    _pair_device(svc1, "phone-b")
    assert svc1.revoke_trust("phone-b")["ok"]

    svc2 = MobileSyncService(db=db)
    assert svc2.is_paired("phone-b")
    assert not svc2.is_trusted("phone-b")
    info = svc2.get_pairing_info("phone-b")
    assert info["revoked"] is True

    row = db.conn.execute(
        "SELECT trusted, revoked FROM mobile_sync_devices WHERE device_id='phone-b'"
    ).fetchone()
    assert row == (0, 1)


def test_unpair_removes_device_persistently(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc1 = MobileSyncService(db=db)
    _pair_device(svc1, "phone-c")
    assert svc1.unpair("phone-c")["ok"]

    svc2 = MobileSyncService(db=db)
    assert not svc2.is_paired("phone-c")
    row = db.conn.execute(
        "SELECT COUNT(*) FROM mobile_sync_devices WHERE device_id='phone-c'"
    ).fetchone()
    assert row[0] == 0


def test_proof_of_possession_requires_real_signature(db) -> None:
    """A key without a signature is rejected; a forged signature is rejected;
    only a real Ed25519 signature over the challenge payload succeeds."""
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    private, raw = _keypair()
    pair = svc.start_pairing()
    payload = (
        f"1.0|{pair['session_id']}|{pair['nonce']}|"
        f"{_fingerprint(raw)}|phone-d"
    ).encode()

    # Public key without signature → rejected.
    no_sig = svc.verify_pairing(
        pair["session_id"], pair["code"], device_id="phone-d",
        public_key=_pub(raw),
    )
    assert not no_sig["ok"]
    assert no_sig["error"] == "SIGNATURE_REQUIRED"
    assert not svc.is_paired("phone-d")

    # Forged signature → rejected.
    forged = svc.verify_pairing(
        pair["session_id"], pair["code"], device_id="phone-d",
        public_key=_pub(raw),
        signature=base64.b64encode(b"x" * 64).decode(),
    )
    assert not forged["ok"]
    assert forged["error"] == "SIGNATURE_INVALID"

    # Real signature → accepted (awaiting approval), then approval grants
    # trust.
    accepted = svc.verify_pairing(
        pair["session_id"], pair["code"], device_id="phone-d",
        public_key=_pub(raw),
        signature=base64.b64encode(private.sign(payload)).decode(),
    )
    assert accepted["ok"]
    assert accepted["status"] == "awaiting_approval"
    assert not svc.is_trusted("phone-d")
    assert svc.approve_device("phone-d")["ok"]
    assert svc.is_trusted("phone-d")


def test_code_only_pairing_is_legacy_and_never_trusts(db) -> None:
    """Code-only pairing: rejected by default; when legacy mode is enabled
    the device awaits approval and is never auto-trusted."""
    from core.mobile_sync_service import MobileSyncService

    # Secure default: rejected.
    svc = MobileSyncService(db=db)
    pair = svc.start_pairing()
    rejected = svc.verify_pairing(pair["session_id"], pair["code"],
                                  device_id="legacy-1")
    assert not rejected["ok"]
    assert rejected["error"] == "SIGNATURE_REQUIRED"

    # Legacy mode: accepted but NOT trusted (manual approval required).
    legacy = MobileSyncService(db=db, legacy_code_pairing_enabled=True)
    pair2 = legacy.start_pairing()
    result = legacy.verify_pairing(pair2["session_id"], pair2["code"],
                                   device_id="legacy-1")
    assert result["ok"]
    assert result["status"] == "awaiting_approval"
    assert legacy.is_paired("legacy-1")
    assert not legacy.is_trusted("legacy-1")
    assert legacy.get_pairing_info("legacy-1")["status"] == "awaiting_approval"
    assert any(
        e["kind"] == "legacy_code_pairing"
        for e in legacy.get_audit_entries()
    ), "legacy pairing must be recorded as an audit entry"


def test_health_reports_persisted_devices(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    _pair_device(svc, "phone-e")
    health = svc.health()
    assert health["paired_devices"] == 1
    assert health["trusted_devices"] == 1
    assert health["persistence"] == "db"
    assert health["secure_pairing_available"] is True
    assert health["insecure_legacy_enabled"] is False
