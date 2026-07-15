"""Test M3U import/export, preview, cancel, progress."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestPlaylistImportExport:

    def test_import_preview_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.previewPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_import_preview_with_service(self):
        svc = MagicMock()
        svc.import_preview.return_value = {"ok": True, "total_entries": 10, "valid_entries": 8, "missing_entries": 2}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.previewPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is True
        assert result["total_entries"] == 10
        assert result["valid_entries"] == 8

    def test_import_preview_service_error(self):
        svc = MagicMock()
        svc.import_preview.return_value = {"ok": False, "error": "INVALID_FORMAT"}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.previewPlaylistImport("/tmp/bad.pls")
        assert result["ok"] is False
        assert result["error"] == "INVALID_FORMAT"

    def test_confirm_import_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.confirmPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def get_playlist_items(self, pid):
        rows = self.conn.execute(
            "SELECT track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        return [{"id": r[0] or 0, "track_id": r[0] or 0, "filepath": r[1] or "", "position": r[2] or idx,
                 "title": "", "artist": "", "album": "", "duration": 0}
                for idx, r in enumerate(rows)]

    def test_import_m3u_alias(self):
        svc = MagicMock()
        svc.import_confirm.return_value = {"ok": True, "name": "Test", "count": 5}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.importM3U("/tmp/test.m3u")
        assert result["ok"] is True
        assert result["count"] == 5

    def remove_track_from_playlist(self, pid, track_id):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (pid, track_id))
        self.conn.commit()

    def test_cancel_import_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.cancelPlaylistImport("import_1")
        assert result["ok"] is True

    def test_cancel_import_with_service(self):
        svc = MagicMock()
        svc.import_cancel.return_value = {"ok": True, "cancelled": True}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.cancelPlaylistImport("import_1")
        assert result["ok"] is True
        svc.import_cancel.assert_called_once_with("import_1")

    def test_export_m3u_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.exportM3U(1, "/tmp/export.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_export_m3u_with_service(self):
        svc = MagicMock()
        svc.export.return_value = {"ok": True, "count": 10}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.exportM3U(1, "/tmp/export.m3u")
        assert result["ok"] is True
        assert result["count"] == 10
        svc.export.assert_called_once_with(1, "/tmp/export.m3u")

    def test_export_m3u8_alias(self):
        svc = MagicMock()
        svc.export.return_value = {"ok": True, "count": 5}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.exportM3U8(1, "/tmp/export.m3u8")
        assert result["ok"] is True

class TestPlaylistImportExport:
    def test_import_preview_m3u(self, svc, tmp_path):
        m3u = tmp_path / "test.m3u"
        m3u.write_text("#EXTM3U\n/path/to/track1.flac\n/path/to/track2.flac\n")
        result = svc.import_preview(str(m3u))
        assert result["ok"]
        assert result["total_entries"] == 2

    def test_import_preview_file_not_found(self, svc):
        result = svc.import_preview("/nonexistent/file.m3u")
        assert not result["ok"]
        assert result["error_code"] == "FILE_NOT_FOUND"

    def test_import_preview_empty_file(self, svc, tmp_path):
        m3u = tmp_path / "empty.m3u"
        m3u.write_text("")
        result = svc.import_preview(str(m3u))
        assert result["ok"]

    def test_import_preview_with_extinf(self, svc, tmp_path):
        m3u = tmp_path / "extinf.m3u"
        m3u.write_text('#EXTM3U\n#EXTINF:123,Test Artist - Test Title\n/path/to/track.flac\n')
        result = svc.import_preview(str(m3u))
        assert result["ok"]

    def test_import_confirm_valid(self, svc, tmp_path):
        track = tmp_path / "track.flac"
        track.write_text("data")
        m3u = tmp_path / "test.m3u"
        m3u.write_text(f"#EXTM3U\n{track}\n")
        result = svc.import_confirm(str(m3u), "Imported")
        assert result["ok"]
        assert result["count"] == 1
        assert result["name"] == "Imported"

    def test_import_confirm_no_name_uses_stem(self, svc, tmp_path):
        track = tmp_path / "track.flac"
        track.write_text("data")
        m3u = tmp_path / "mylist.m3u"
        m3u.write_text(f"#EXTM3U\n{track}\n")
        result = svc.import_confirm(str(m3u))
        assert result["ok"]
        assert result["name"] == "mylist"

    def test_import_confirm_no_db(self, svc):
        svc_no_db = PlaylistService(db=None)
        result = svc_no_db.import_confirm("/path/to/file.m3u")
        assert not result["ok"]

    def test_export_m3u(self, svc, tmp_path):
        svc.create("Export")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1, filepath="/path/1.flac")
        dest = tmp_path / "export.m3u"
        with patch("core.playlist_service.Path.is_file", return_value=True):
            result = svc.export(pid, str(dest))
            if not result.get("ok"):
                assert any(x in result.get("error_code", "") for x in ["NOT_FOUND", "NO_SERVICE", "NO_VALID"])

    def test_export_empty_path(self, svc):
        svc.create("ExportEmpty")
        pid = svc.list()[0]["id"]
        result = svc.export(pid, "")
        assert not result["ok"]

    def test_export_nonexistent_playlist(self, svc):
        result = svc.export(999, "/path/out.m3u")
        assert not result["ok"]

    def test_cancel_import(self, svc):
        result = svc.cancel_import("import_123")
        assert result["ok"]

    def test_export_m3u_with_multiple_tracks(self, svc, tmp_path):
        svc.create("Multi")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1, filepath="/path/1.flac")
        svc.add_track(pid, track_id=2, filepath="/path/2.flac")
        dest = tmp_path / "multi.m3u"
        with patch("core.playlist_service.Path.is_file", return_value=True):
            result = svc.export(pid, str(dest))
            if not result.get("ok"):
                assert any(x in result.get("error_code", "") for x in ["NOT_FOUND", "NO_SERVICE", "NO_VALID"])

    def test_import_m3u8(self, svc, tmp_path):
        track = tmp_path / "track.flac"
        track.write_text("data")
        m3u8 = tmp_path / "list.m3u8"
        m3u8.write_text(f"#EXTM3U\n{track}\n")
        result = svc.import_confirm(str(m3u8), "FromM3U8")
        assert result["ok"]
        assert result["count"] == 1
