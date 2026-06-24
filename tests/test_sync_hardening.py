"""Tests for Michi Sync Suite hardening."""
import json
import tempfile
import os
from unittest.mock import MagicMock, patch


# ── Delta manifest endpoint ──

def _request_delta(method="GET", path="/api/sync/manifest/delta",
                   body=None, srv=None, headers=None):
    """Simulate an HTTP request to the sync server delta endpoint."""
    from sync.sync_server import SyncRequestHandler
    import io as _io

    h = SyncRequestHandler.__new__(SyncRequestHandler)
    SyncRequestHandler.server_ref = srv
    h.path = path
    h.headers = headers or {}
    h.status_code = None
    h.response_data = None

    def _send_json(data, status=200):
        h.status_code = status
        h.response_data = data
        h.send_response = lambda c: None
        h.send_header = lambda *a: None
        h.end_headers = lambda: None
    h._send_json = _send_json

    h.rfile = _io.BytesIO(b"")
    h.wfile = _io.BytesIO()

    if body:
        h.rfile = _io.BytesIO(json.dumps(body).encode() if isinstance(body, dict) else body)
        h.headers["Content-Length"] = str(len(json.dumps(body).encode() if isinstance(body, dict) else body))

    if method == "GET":
        h.do_GET()
    elif method == "POST":
        h.do_POST()
    return h.status_code, h.response_data


class TestDeltaEndpoint:
    def test_delta_no_auth_returns_401(self):
        code, data = _request_delta(path="/api/sync/manifest/delta", headers={})
        assert code == 401

    def test_delta_wrong_token_returns_401(self):
        code, data = _request_delta(
            path="/api/sync/manifest/delta",
            headers={"Authorization": "Bearer wrong"})
        assert code == 401

    def test_delta_valid_requests(self):
        """Test delta endpoint with valid auth and provider."""
        from sync.sync_protocol import SessionToken
        session = SessionToken(
            token="test-token",
            client_device_id="dev1",
        )
        srv = MagicMock()
        srv._sessions = {"test-token": session}
        srv._delta_provider = MagicMock(return_value={"added": [], "modified": [], "removed": []})

        # Valid request
        code, data = _request_delta(
            path="/api/sync/manifest/delta?device_id=dev1&since=1700000000",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 200
        srv._delta_provider.assert_called_once()

        # Provider called with correct since
        called_since = srv._delta_provider.call_args[0][1]
        assert called_since == 1700000000.0

    def test_delta_missing_device_id_returns_400(self):
        from sync.sync_protocol import SessionToken
        srv = MagicMock()
        srv._sessions = {"test-token": SessionToken(token="test-token", client_device_id="dev1")}
        srv._delta_provider = MagicMock()
        code, data = _request_delta(
            path="/api/sync/manifest/delta",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 400

    def test_delta_wrong_device_id_returns_403(self):
        from sync.sync_protocol import SessionToken
        srv = MagicMock()
        srv._sessions = {"test-token": SessionToken(token="test-token", client_device_id="dev1")}
        srv._delta_provider = MagicMock()
        code, data = _request_delta(
            path="/api/sync/manifest/delta?device_id=dev2",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 403

    def test_delta_no_provider_returns_503(self):
        from sync.sync_protocol import SessionToken
        srv = MagicMock()
        srv._delta_provider = None
        srv._sessions = {"test-token": SessionToken(token="test-token", client_device_id="dev1")}
        code, data = _request_delta(
            path="/api/sync/manifest/delta?device_id=dev1",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 503

    def test_delta_none_result_returns_404(self):
        from sync.sync_protocol import SessionToken
        srv = MagicMock()
        srv._delta_provider = MagicMock(return_value=None)
        srv._sessions = {"test-token": SessionToken(token="test-token", client_device_id="dev1")}
        code, data = _request_delta(
            path="/api/sync/manifest/delta?device_id=dev1",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 404

    def test_delta_invalid_since_falls_back(self):
        from sync.sync_protocol import SessionToken
        srv = MagicMock()
        srv._delta_provider = MagicMock(return_value={"tracks": []})
        srv._sessions = {"test-token": SessionToken(token="test-token", client_device_id="dev1")}
        code, data = _request_delta(
            path="/api/sync/manifest/delta?device_id=dev1&since=notanumber",
            headers={"Authorization": "Bearer test-token"},
            srv=srv)
        assert code == 200
        called_since = srv._delta_provider.call_args[0][1]
        assert called_since == 0.0


# ── Manifest store ──

class TestManifestStore:
    def test_history_limits_to_20(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with patch("ui.services.sync_manifest_store._BASE_DIR", tmpdir):
                from ui.services.sync_manifest_store import SyncManifestStore
                store = SyncManifestStore()
                for i in range(25):
                    store.save("dev1", {
                        "manifest_id": f"m-{i}",
                        "created_at": "2025-01-01T00:00:00",
                        "total_tracks": i,
                        "total_size": i * 1000,
                        "tracks": [{"id": f"t{i}"}],
                    })
                history = store.load_history("dev1")
                assert len(history) == 20
                assert history[0]["manifest_id"] == "m-5"  # first 5 were pruned
                assert history[-1]["manifest_id"] == "m-24"
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_latest_returns_manifest(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with patch("ui.services.sync_manifest_store._BASE_DIR", tmpdir):
                from ui.services.sync_manifest_store import SyncManifestStore
                store = SyncManifestStore()
                manifest = {
                    "manifest_id": "abc",
                    "tracks": [{"id": "t1"}, {"id": "t2"}],
                }
                store.save("dev1", manifest, public=True)
                loaded = store.load_latest("dev1")
                # With public=True, save stores manifest.get("tracks", manifest)
                expected = manifest["tracks"]
                assert loaded == expected
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_latest_missing_returns_none(self):
        from ui.services.sync_manifest_store import SyncManifestStore
        store = SyncManifestStore()
        assert store.load_latest("nonexistent-device") is None

    def test_list_devices_returns_device_ids(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with patch("ui.services.sync_manifest_store._BASE_DIR", tmpdir):
                from ui.services.sync_manifest_store import SyncManifestStore
                store = SyncManifestStore()
                store.save("dev-a", {"tracks": []})
                store.save("dev-b", {"tracks": []})
                devices = store.list_devices()
                assert "dev-a" in devices
                assert "dev-b" in devices
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── Sidebar dynamic peers ──

class TestSidebarSyncPeers:
    def test_sidebar_adds_sync_peers(self):
        mock_db = MagicMock()
        mock_db.get_playlists.return_value = []
        mock_sidebar = MagicMock()
        mock_sidebar.item_clicked = MagicMock()
        from ui.sidebar_controller import SidebarController
        ctrl = SidebarController(mock_sidebar, mock_db)

        peers = [
            {"alias": "Pixel 7", "device_id": "sync_abc", "device_type": "android"},
        ]

        ctrl.rebuild([], sync_peers=peers)
        calls = mock_sidebar.add_item.call_args_list
        dev_calls = [c for c in calls if c[0][0] == "dev"]
        keys = [c[0][1] for c in dev_calls]
        assert "dev:sync:sync_abc" in keys
        # Static devices_page item still present
        assert "devices_page" in keys

    def test_dev_sync_navigates_to_devices_page(self):
        """Verify that dev:sync:NN routes to _show_devices_page in window.py."""
        # read the NAV_ROUTES dict
        from ui.window import NAV_ROUTES
        assert NAV_ROUTES.get("devices_page") == "_show_devices_page"


# ── ensure_file_hash ──

class TestEnsureFileHash:
    def test_returns_empty_on_missing_file(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            from library.library_db import LibraryDB
            db_path = os.path.join(tmpdir, "test.db")
            db = LibraryDB(db_path)
            result = db.ensure_file_hash("/nonexistent/file.mp3")
            assert result == ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_logs_warning_on_stat_failure(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            from library.library_db import LibraryDB
            db_path = os.path.join(tmpdir, "test.db")
            db = LibraryDB(db_path)
            with patch("library.library_db.logger") as mock_log:
                db.ensure_file_hash("/nonexistent/file.mp3")
                mock_log.warning.assert_called()
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_computes_and_caches_hash(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            audio = os.path.join(tmpdir, "x.mp3")
            with open(audio, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" * 500)

            from library.library_db import LibraryDB
            db_path = os.path.join(tmpdir, "test.db")
            db = LibraryDB(db_path)
            db._conn.execute(
                "INSERT INTO media_items (filepath,filename,directory,ext,kind,mtime) "
                "VALUES (?,?,?,?,?,?)",
                (audio, "x.mp3", tmpdir, ".mp3", "audio", os.path.getmtime(audio)))
            db._conn.commit()

            h1 = db.ensure_file_hash(audio)
            assert len(h1) == 64

            # Second call should return cached value (no re-read)
            h2 = db.ensure_file_hash(audio)
            assert h1 == h2

            # Verify stored in DB
            row = db._conn.execute(
                "SELECT file_hash FROM media_items WHERE filepath=?", (audio,)).fetchone()
            assert row[0] == h1
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
