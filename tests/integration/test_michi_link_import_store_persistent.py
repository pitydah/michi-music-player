"""Integration (debt D3a): ImportStore committed sessions survive restarts.

The store persists committed sessions to a SQLite ledger; a new store (or a
restarted server listener) created with the same ``db_path`` restores the
committed records with their item metadata (checksums, sizes, filenames).
Rollback removes the record from the ledger. The server flow runs against the
REAL in-process listener harness shared with test_michi_link_import_session.
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


class _PersistentServerHarness:
    """Real listener whose ImportStore uses a tmp SQLite ledger path."""

    def __init__(self, tmp_path, store_path: str):
        from library.library_db import LibraryDB
        from core.sync.device_registry import DeviceRegistry
        from core.mobile_sync_service import MobileSyncService

        self.db = LibraryDB(str(tmp_path / "library.db"))
        self.registry = DeviceRegistry(str(tmp_path / "paired.json"))
        self.svc = MobileSyncService(
            db=self.db, registry=self.registry, port=0,
            import_store_path=store_path,
        )
        result = self.svc.start()
        assert result.get("ok"), result
        self.port = self.svc.listening_port
        assert self.port > 0

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
        private, raw = _ed25519_keypair()
        pub_b64 = base64.b64encode(raw).decode()
        fp = hashlib.sha256(raw).hexdigest()

        pair = self.svc.start_pairing()
        challenge = self._post("/api/v1/pair/challenge", {
            "session_id": pair["session_id"],
        })
        assert challenge.get("ok"), challenge
        nonce = challenge["nonce"]

        signature = base64.b64encode(private.sign(_payload(
            "1.0", pair["session_id"], nonce, fp, device_id))).decode()
        req_resp = self._post("/api/v1/pair/request", {
            "session_id": pair["session_id"], "nonce": nonce,
            "public_key": pub_b64, "signature": signature,
            "device_id": device_id, "name": "Test Phone",
            "protocol_version": "1.0",
        })
        assert req_resp.get("ok"), req_resp
        assert self.svc.approve_device(device_id)["ok"]

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


def _audio_bytes(n: int = 1) -> bytes:
    return bytes([(i * 7 + n) % 256 for i in range(4096)])


class TestImportStorePersistence:
    def test_commit_survives_restart(self, tmp_path) -> None:
        from integrations.michi_link.import_store import ImportStore

        store = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        session = store.create_session(source="device-a")
        store.add_track(session.session_id, "t1", _audio_bytes(1),
                        checksum="abc123", filename="song.flac")
        store.add_artwork(session.session_id, "cov1", b"art",
                          checksum="def456")
        store.add_playlist(session.session_id, "pl1", "Mixtape", ["t1"])
        committed = store.commit(session.session_id)
        assert committed is not None
        assert committed.state == "committed"

        restarted = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        restored = restarted.get(session.session_id)
        assert restored is not None
        assert restored.state == "committed"
        assert restored.committed_at == committed.committed_at
        assert restored.source == "device-a"
        assert "t1" in restored.tracks
        assert restored.tracks["t1"].checksum == "abc123"
        assert restored.tracks["t1"].size == len(_audio_bytes(1))
        assert restored.tracks["t1"].filename == "song.flac"
        assert restored.artwork["cov1"].checksum == "def456"
        assert restored.playlists["pl1"].name == "Mixtape"
        assert restored.playlists["pl1"].track_ids == ["t1"]

    def test_rollback_removes(self, tmp_path) -> None:
        from integrations.michi_link.import_store import ImportStore

        store = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        session = store.create_session(source="device-b")
        store.add_track(session.session_id, "t1", _audio_bytes(1),
                        checksum="xyz")
        store.rollback(session.session_id)

        restarted = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        assert restarted.get(session.session_id) is None

    def test_pending_session_not_persisted(self, tmp_path) -> None:
        from integrations.michi_link.import_store import ImportStore

        store = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        session = store.create_session(source="device-c")
        store.add_track(session.session_id, "t1", _audio_bytes(1))

        restarted = ImportStore(db_path=str(tmp_path / "imports.sqlite"))
        assert restarted.get(session.session_id) is None


class TestServerReadbackAfterRestart:
    def test_readback_after_restart(self, tmp_path) -> None:
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )

        store_path = str(tmp_path / "imports.sqlite")
        harness = _PersistentServerHarness(tmp_path, store_path)
        server = harness.pair(device_id="phone-persist")
        svc = ImportToServerService()

        created = svc.create_session(server, ["t1"])
        assert created.ok
        sid = created.data["session_id"]
        up = svc.upload_track(sid, "t1", local_data=_audio_bytes(1))
        assert up.ok
        committed = svc.commit(sid)
        assert committed.ok, committed.message
        harness.stop()

        restarted = _PersistentServerHarness(tmp_path, store_path)
        try:
            server2 = restarted.pair(device_id="phone-persist")
            status_code, status = restarted.get(
                f"/api/v1/import/session/status?session_id={sid}", server2)
            assert status_code == 200
            assert status["state"] == "committed"
            assert status["uploaded_tracks"] == 1
            assert status["session_id"] == sid

            info_code, info = restarted.get(
                f"/api/v1/import/track/info?session_id={sid}&track_id=t1",
                server2)
            assert info_code == 200
            assert info["stored"] is True
            assert info["checksum"] == hashlib.sha256(_audio_bytes(1)).hexdigest()
        finally:
            restarted.stop()

    def test_rolled_back_session_gone_after_restart(self, tmp_path) -> None:
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )

        store_path = str(tmp_path / "imports.sqlite")
        harness = _PersistentServerHarness(tmp_path, store_path)
        server = harness.pair(device_id="phone-rollback-persist")
        svc = ImportToServerService()

        created = svc.create_session(server, ["t1"])
        sid = created.data["session_id"]
        assert svc.upload_track(sid, "t1", local_data=_audio_bytes(1)).ok
        assert svc.rollback(sid).ok
        harness.stop()

        restarted = _PersistentServerHarness(tmp_path, store_path)
        try:
            server2 = restarted.pair(device_id="phone-rollback-persist")
            with pytest.raises(urllib.error.HTTPError) as exc:
                restarted.get(
                    f"/api/v1/import/session/status?session_id={sid}", server2)
            assert exc.value.code == 404
        finally:
            restarted.stop()
