"""Integration: MobileSyncService persistent pairing (Slice 7).

Pairing/trust/revocation survive service restarts through the
``mobile_sync_devices`` table (migration 8), and proof of possession
(challenge/response) gates pairing for devices that present a public key.
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


def test_pairing_survives_restart(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc1 = MobileSyncService(db=db)
    pair = svc1.start_pairing()
    challenge = svc1.get_pairing_challenge(pair["session_id"])["challenge"]
    result = svc1.verify_pairing(
        pair["session_id"], pair["code"],
        device_name="Phone A", device_id="phone-a",
        public_key="pk-a", fingerprint="fp-a",
        proof=_proof(pair["code"], challenge),
    )
    assert result["ok"]

    # New instance, same DB: the device is still paired and trusted.
    svc2 = MobileSyncService(db=db)
    assert svc2.is_paired("phone-a")
    assert svc2.is_trusted("phone-a")
    info = svc2.get_pairing_info("phone-a")
    assert info is not None
    assert info["name"] == "Phone A"
    assert info["public_key"] == "pk-a"
    assert info["trusted"] is True

    # And the DB row exists with the device identity columns.
    row = db.conn.execute(
        "SELECT device_id, name, public_key, fingerprint, trusted, revoked "
        "FROM mobile_sync_devices WHERE device_id='phone-a'"
    ).fetchone()
    assert row is not None
    assert row[2] == "pk-a"
    assert row[3] == "fp-a"
    assert row[4] == 1


def test_revocation_survives_restart(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc1 = MobileSyncService(db=db)
    pair = svc1.start_pairing()
    challenge = svc1.get_pairing_challenge(pair["session_id"])["challenge"]
    svc1.verify_pairing(
        pair["session_id"], pair["code"],
        device_id="phone-b", public_key="pk-b",
        proof=_proof(pair["code"], challenge),
    )
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
    pair = svc1.start_pairing()
    challenge = svc1.get_pairing_challenge(pair["session_id"])["challenge"]
    svc1.verify_pairing(
        pair["session_id"], pair["code"],
        device_id="phone-c", public_key="pk-c",
        proof=_proof(pair["code"], challenge),
    )
    assert svc1.unpair("phone-c")["ok"]

    svc2 = MobileSyncService(db=db)
    assert not svc2.is_paired("phone-c")
    row = db.conn.execute(
        "SELECT COUNT(*) FROM mobile_sync_devices WHERE device_id='phone-c'"
    ).fetchone()
    assert row[0] == 0


def test_proof_of_possession_passes_only_with_right_key(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    pair = svc.start_pairing()
    sid, code = pair["session_id"], pair["code"]
    challenge = svc.get_pairing_challenge(sid)["challenge"]

    # Wrong proof → rejected.
    wrong = _proof("000000", challenge)
    rejected = svc.verify_pairing(
        sid, code, device_id="phone-d", public_key="pk-d",
        proof=wrong,
    )
    assert not rejected["ok"]
    assert rejected["error"] == "PROOF_INVALID"
    assert not svc.is_paired("phone-d")

    # Public key without proof → rejected.
    no_proof = svc.verify_pairing(
        sid, code, device_id="phone-d", public_key="pk-d",
    )
    assert not no_proof["ok"]
    assert no_proof["error"] == "PROOF_INVALID"

    # Right proof → accepted.
    accepted = svc.verify_pairing(
        sid, code, device_id="phone-d", public_key="pk-d",
        fingerprint="fp-d", proof=_proof(code, challenge),
    )
    assert accepted["ok"]
    assert svc.is_trusted("phone-d")


def test_code_only_pairing_still_supported(db) -> None:
    """Legacy clients without a public key keep code-only pairing."""
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    pair = svc.start_pairing()
    result = svc.verify_pairing(pair["session_id"], pair["code"],
                                device_id="legacy-1")
    assert result["ok"]
    assert svc.is_trusted("legacy-1")


def test_health_reports_persisted_devices(db) -> None:
    from core.mobile_sync_service import MobileSyncService

    svc = MobileSyncService(db=db)
    pair = svc.start_pairing()
    challenge = svc.get_pairing_challenge(pair["session_id"])["challenge"]
    svc.verify_pairing(
        pair["session_id"], pair["code"],
        device_id="phone-e", public_key="pk-e",
        proof=_proof(pair["code"], challenge),
    )
    health = svc.health()
    assert health["paired_devices"] == 1
    assert health["trusted_devices"] == 1
    assert health["persistence"] == "db"
