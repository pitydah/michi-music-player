"""Integration: ImportToServerService against the real in-process server.

The harness is the REAL production listener: MobileSyncService.start() boots
``SyncRequestHandler`` with the Michi Link v1 routes; the client pairs over
HTTP with a REAL Ed25519 signature (``/api/v1/pair/challenge`` +
``/api/v1/pair/request``), the device is approved desktop-side, and the
approved device exchanges a token over ``/api/v1/pair/code``. It then drives
a full import session: preflight → session → track + artwork + playlist
upload → remote readback → checksum verification → commit. Failures (session
expired, rollback with partial uploads) are exercised against the same real
server.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request

import pytest

from integrations.michi_link.client import RemoteServerInfo


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


def _payload(protocol_version: str, session_id: str, nonce: str,
             fingerprint: str, device_id: str) -> bytes:
    return (
        f"{protocol_version}|{session_id}|{nonce}|{fingerprint}|{device_id}"
    ).encode()


class _ServerHarness:
    """Real listener + LibraryDB + temp DeviceRegistry on an ephemeral port."""

    def __init__(self, tmp_path, insert_track: bool = False):
        from library.library_db import LibraryDB
        from core.sync.device_registry import DeviceRegistry
        from core.mobile_sync_service import MobileSyncService

        self.db = LibraryDB(str(tmp_path / "library.db"))
        if insert_track:
            self._insert_track()
        self.registry = DeviceRegistry(str(tmp_path / "paired.json"))
        self.svc = MobileSyncService(db=self.db, registry=self.registry, port=0)
        result = self.svc.start()
        assert result.get("ok"), result
        self.port = self.svc.listening_port
        assert self.port > 0

    def _insert_track(self) -> None:
        self.db.conn.execute(
            "INSERT INTO media_items (filepath, filename, directory, ext, "
            "kind, size, mtime, duration, title, artist, album) "
            "VALUES (?, ?, ?, ?, 'song', ?, 0, ?, ?, ?, ?)",
            ("/music/server_known.flac", "server_known.flac", "/music",
             ".flac", 1000, 2.5, "Server Known", "Server Artist", "Srv Album"),
        )
        self.db.conn.commit()

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())

    def pair(self, device_id: str = "test-phone") -> RemoteServerInfo:
        """Signature pairing over HTTP + desktop approval + token exchange."""
        private, raw = _ed25519_keypair()
        pub_b64 = base64.b64encode(raw).decode()
        fp = hashlib.sha256(raw).hexdigest()

        # 1. Session + nonce over the wire.
        pair = self.svc.start_pairing()
        challenge = self._post("/api/v1/pair/challenge", {
            "session_id": pair["session_id"],
        })
        assert challenge.get("ok"), challenge
        nonce = challenge["nonce"]

        # 2. Signed pair request → awaiting_approval.
        signature = base64.b64encode(private.sign(_payload(
            "1.0", pair["session_id"], nonce, fp, device_id))).decode()
        req_resp = self._post("/api/v1/pair/request", {
            "session_id": pair["session_id"], "nonce": nonce,
            "public_key": pub_b64, "signature": signature,
            "device_id": device_id, "name": "Test Phone",
            "protocol_version": "1.0",
        })
        assert req_resp.get("ok"), req_resp
        assert req_resp.get("status") == "awaiting_approval", req_resp

        # 3. Desktop-side user approval.
        assert self.svc.approve_device(device_id)["ok"]

        # 4. Token exchange: the approved device re-pairs with the same key.
        pair2 = self.svc.start_pairing()
        sig2 = base64.b64encode(private.sign(_payload(
            "1.0", pair2["session_id"], pair2["nonce"], fp, device_id
        ))).decode()
        resp = self._post("/api/v1/pair/code", {
            "session_id": pair2["session_id"], "code": pair2["code"],
            "device_id": device_id, "name": "Test Phone",
            "public_key": pub_b64, "fingerprint": fp,
            "signature": sig2, "protocol_version": "1.0",
        })
        assert resp.get("success"), resp
        return RemoteServerInfo(
            host="127.0.0.1", port=self.port,
            device_token=resp["device_token"],
            device_id=resp["device_id"],
            alias="Michi Music Player",
        )

    def get(self, path: str, server: RemoteServerInfo):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", method="GET",
            headers={
                "Authorization": f"Bearer {server.device_token}",
                "X-Michi-Device-Id": server.device_id,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())

    def stop(self) -> None:
        self.svc.stop()


@pytest.fixture
def harness(tmp_path):
    h = _ServerHarness(tmp_path)
    yield h
    h.stop()


def _audio_bytes(n: int = 1) -> bytes:
    return bytes([(i * 7 + n) % 256 for i in range(4096)])


def test_full_import_session_commit_with_readback(harness) -> None:
    from integrations.michi_link.services.import_to_server_service import (
        ImportToServerService,
    )
    server = harness.pair(device_id="phone-full")
    svc = ImportToServerService()

    created = svc.create_session(server, ["t1", "t2"])
    assert created.ok
    sid = created.data["session_id"]

    up1 = svc.upload_track(sid, "t1", local_data=_audio_bytes(1))
    assert up1.ok, up1.message
    assert up1.data["mapping_status"] == "confirmed"
    up2 = svc.upload_track(sid, "t2", local_data=_audio_bytes(2))
    assert up2.ok

    art = svc.upload_artwork(sid, "cover_x", artwork_data=b"fake_art_data")
    assert art.ok, art.message
    pl = svc.upload_playlist(sid, {
        "playlist_id": "pl_1", "name": "Mixtape",
        "track_ids": ["t1", "t2"],
    })
    assert pl.ok, pl.message

    # Remote readback: the server really holds the items.
    status = svc.readback(sid)
    assert status.ok, status.message
    assert status.data["state"] == "pending"
    assert status.data["server_tracks"] == 2
    assert status.data["server_artwork"] == 1
    assert status.data["server_playlists"] == 1

    # Checksum verification by readback.
    verified = svc.verify_upload(sid, "t1")
    assert verified.ok and verified.data["verified"] is True

    # Commit → server confirms + readback matches.
    committed = svc.commit(sid)
    assert committed.ok, committed.message
    assert committed.data["readback_verified"] is True
    assert committed.data["mapping"]["t1"].startswith(sid)

    # The session is closed server-side; a second commit is rejected.
    second = svc.commit(sid)
    assert not second.ok


def test_preflight_against_real_server_library(tmp_path) -> None:
    harness = _ServerHarness(tmp_path, insert_track=True)
    try:
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        server = harness.pair(device_id="phone-preflight")
        svc = ImportToServerService()
        identity = TrackIdentity(
            local_track_id="known_1", file_size=1000, duration_ms=2500.0,
            title="Server Known", artist="Server Artist",
            normalized_title="server known", normalized_artist="server artist",
            quick_hash="", content_hash="",
        )
        result = svc.preflight(server, [identity])
        assert result.ok
        assert result.data["known_1"]["exists"] is True

        missing = TrackIdentity(
            local_track_id="missing_1", file_size=42, duration_ms=100.0,
            title="Nope", artist="Nobody",
            normalized_title="nope", normalized_artist="nobody",
        )
        result2 = svc.preflight(server, [missing])
        assert result2.ok
        assert result2.data["missing_1"]["exists"] is False
    finally:
        harness.stop()


def test_failed_upload_then_rollback_leaves_no_partial_items(harness) -> None:
    from integrations.michi_link.services.import_to_server_service import (
        ImportToServerService,
    )
    server = harness.pair(device_id="phone-rollback")
    svc = ImportToServerService()

    created = svc.create_session(server, ["ok1", "bad2"])
    sid = created.data["session_id"]

    assert svc.upload_track(sid, "ok1", local_data=_audio_bytes(1)).ok

    # Force a server-side failure for the second track: drop the session
    # server-side (simulates an expired/evicted session mid-import).
    harness.svc._listener._import_store.drop(sid)
    failed = svc.upload_track(sid, "bad2", local_data=_audio_bytes(2))
    assert not failed.ok

    # Rollback must confirm server-side (session already gone → 404 is the
    # server's explicit "nothing to roll back").
    rolled = svc.rollback(sid)
    assert rolled.ok, rolled.message
    assert svc.get_session(sid) is None

    # No partial items remain: the readback endpoint 404s.
    from urllib.error import HTTPError
    try:
        harness.get(f"/api/v1/import/session/status?session_id={sid}", server)
        raise AssertionError("session should be gone after rollback")
    except HTTPError as e:
        assert e.code == 404


def test_expired_session_errors_and_requires_repair(harness) -> None:
    from integrations.michi_link.services.import_to_server_service import (
        ImportToServerService,
    )
    server = harness.pair(device_id="phone-expired")
    svc = ImportToServerService()

    created = svc.create_session(server, ["t1"])
    sid = created.data["session_id"]
    assert svc.upload_track(sid, "t1", local_data=_audio_bytes(1)).ok

    # Expire the session server-side (real expiry path: TTL elapsed).
    store = harness.svc._listener._import_store
    store._sessions[sid].expires_at = 0

    committed = svc.commit(sid)
    assert not committed.ok
    assert committed.code == "SESSION_EXPIRED", committed

    # The service offers the explicit re-pair path: a fresh session works.
    created2 = svc.create_session(server, ["t1"])
    assert created2.ok
    assert created2.data["session_id"] != sid
    up = svc.upload_track(created2.data["session_id"], "t1",
                          local_data=_audio_bytes(1))
    assert up.ok


def test_remote_library_playlists_readback(harness) -> None:
    from integrations.michi_link.services.remote_library_service import (
        RemoteLibraryService,
    )
    server = harness.pair(device_id="phone-lib")
    rls = RemoteLibraryService()
    result = rls.get_playlists(server)
    assert result.ok
    assert isinstance(result.data["playlists"], list)


def test_remote_library_playlists_unavailable_when_disconnected() -> None:
    from integrations.michi_link.services.remote_library_service import (
        RemoteLibraryService,
    )
    from integrations.michi_link.client import RemoteServerInfo
    server = RemoteServerInfo(host="127.0.0.1", port=1)
    rls = RemoteLibraryService()
    result = rls.get_playlists(server)
    assert not result.ok
    assert result.code == "REMOTE_UNAVAILABLE"
