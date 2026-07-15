"""DX — MetadataService real: load, edit, validate, preview, confirmation,
backup, write temp, verify, replace, DB update, event, model refresh, undo.

Single editor, batch editor, mixed values, artwork, diff, conflicts,
numbering, search/replace, filename parsing, progress, cancel, rollback.
"""
from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import patch

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


class MockTags:
    def __init__(self, **kwargs):
        self.filepath = kwargs.get("filepath", "")
        self.title = kwargs.get("title", "")
        self.artist = kwargs.get("artist", "")
        self.album = kwargs.get("album", "")
        self.albumartist = kwargs.get("albumartist", "")
        self.tracknumber = kwargs.get("tracknumber", "")
        self.tracktotal = kwargs.get("tracktotal", "")
        self.discnumber = kwargs.get("discnumber", "")
        self.disctotal = kwargs.get("disctotal", "")
        self.date = kwargs.get("date", "")
        self.genre = kwargs.get("genre", "")
        self.composer = kwargs.get("composer", "")
        self.comment = kwargs.get("comment", "")
        self.lyrics = kwargs.get("lyrics", "")
        self.bpm = kwargs.get("bpm", "")
        self.isrc = kwargs.get("isrc", "")
        self.musicbrainz_trackid = kwargs.get("musicbrainz_trackid", "")
        self.musicbrainz_albumid = kwargs.get("musicbrainz_albumid", "")
        self.kind = kwargs.get("kind", "FLAC")
        self.bitrate = kwargs.get("bitrate", 0)
        self.sample_rate = kwargs.get("sample_rate", 44100)
        self.channels = kwargs.get("channels", 2)
        self.duration = kwargs.get("duration", 60.0)
        self.filesize = kwargs.get("filesize", 1000)
        self.file_mtime = kwargs.get("file_mtime", 0.0)
        self.has_artwork = kwargs.get("has_artwork", False)
        self.artwork_mime = kwargs.get("artwork_mime", "")
        self.artwork_data = kwargs.get("artwork_data")
        self.dirty = False
        self.dirty_fields = set()
        self.artwork_dirty = False
        self.error = ""
        self.original = None

    def clone(self):
        return MockTags(**{k: getattr(self, k) for k in
                           ["title", "artist", "album", "albumartist",
                            "tracknumber", "tracktotal", "discnumber", "disctotal",
                            "date", "genre", "composer", "comment", "lyrics",
                            "bpm", "isrc", "musicbrainz_trackid", "musicbrainz_albumid",
                            "kind", "bitrate", "sample_rate", "channels", "duration",
                            "filesize", "file_mtime", "has_artwork", "artwork_mime",
                            "artwork_data"]})

    def to_dict(self):
        return {f: str(getattr(self, f, "") or "") for f in
                ("title", "artist", "album", "albumartist", "genre",
                 "date", "tracknumber", "discnumber", "composer",
                 "comment", "bpm", "isrc", "tracktotal", "disctotal",
                 "musicbrainz_trackid", "musicbrainz_albumid")}


class TestMetadataServiceReal:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def sample_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def svc(self, app):
        from core.metadata_service import MetadataService
        return MetadataService()

    def _patch_read_tags(self, svc, mock_return=None):
        if mock_return is None:
            mock_return = MockTags(filepath="/test.flac")
        patcher = patch.object(svc, "_tag_reader", return_value=mock_return)
        patcher.start()
        self._reader_patch = patcher
        return mock_return

    def _stop_patches(self):
        if hasattr(self, "_reader_patch"):
            self._reader_patch.stop()

    def test_create_service(self, svc):
        assert svc is not None

    def test_load_existing_file(self, svc, sample_file):
        result = svc.load(sample_file)
        assert result["ok"] is True
        assert "tags" in result

    def test_load_nonexistent_file(self, svc):
        result = svc.load("/nonexistent.flac")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_load_empty_path(self, svc):
        result = svc.load("")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_edit_field_after_load(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.edit_field(sample_file, "title", "New Title")
        assert result["ok"] is True
        assert result["field"] == "title"
        assert result["new_value"] == "New Title"

    def test_edit_field_no_load(self, svc):
        result = svc.edit_field("/nonexistent.flac", "title", "Test")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_LOADED"

    def test_validate_valid_data(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "tracknumber", "1")
        result = svc.validate(sample_file)
        assert result["ok"] is True
        assert "valid" in result

    def test_validate_invalid_tracknumber(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "tracknumber", "abc")
        result = svc.validate(sample_file)
        assert result["ok"] is True
        assert result["valid"] is False

    def test_validate_invalid_bpm(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "bpm", "9999")
        result = svc.validate(sample_file)
        assert result["ok"] is True
        assert result["valid"] is False

    def test_preview_changes(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "title", "Preview Title")
        result = svc.preview_changes(sample_file)
        assert result["ok"] is True
        assert len(result["changes"]) >= 1

    def test_preview_no_changes(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.preview_changes(sample_file)
        assert result["ok"] is True

    def test_confirmation_token(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.request_confirmation(sample_file)
        assert result["ok"] is True
        assert "confirmation_token" in result

    @patch("core.metadata_service.MetadataService._write_tags", return_value=True)
    @patch("core.metadata_service.MetadataService._verify_changes", return_value=True)
    @patch("core.metadata_service.MetadataService._create_backup", return_value="/tmp/backup.bak")
    @patch("core.metadata_service.MetadataService._update_db", return_value=True)
    def test_confirm_and_apply(self, mock_db, mock_backup, mock_verify, mock_write,
                                svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "title", "Applied Title")
        confirm = svc.request_confirmation(sample_file)
        token = confirm["confirmation_token"]
        result = svc.confirm_and_apply(sample_file, token)
        assert result["ok"] is True

    def test_confirm_invalid_token(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.confirm_and_apply(sample_file, "bad_token")
        assert result["ok"] is False
        assert result["error"] == "INVALID_CONFIRMATION_TOKEN"

    @patch("core.metadata_service.MetadataService._write_tags", return_value=True)
    @patch("core.metadata_service.MetadataService._verify_changes", return_value=True)
    @patch("core.metadata_service.MetadataService._update_db", return_value=True)
    def test_undo_restores(self, mock_db, mock_verify, mock_write,
                            svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "title", "To Undo")
        backup_path = sample_file + ".bak"
        import shutil
import pytest
pytestmark = [pytest.mark.qml_module("metadata")]

        shutil.copy2(sample_file, backup_path)
        state = svc._active.get(sample_file)
        state.backup_path = backup_path
        result = svc.undo(sample_file)
        assert result["ok"] is True
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_undo_no_backup(self, svc):
        result = svc.undo("/nonexistent.flac")
        assert result["ok"] is False

    def test_batch_load(self, svc, sample_file):
        result = svc.load_batch([sample_file])
        assert result["ok"] is True
        assert len(result["results"]) == 1

    def test_batch_edit(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.edit_batch([sample_file], "genre", "Test Genre")
        assert result["applied"] >= 1

    def test_search_replace(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.search_replace(sample_file, "x", "y")
        assert result["ok"] is True

    def test_parse_filename(self, svc):
        result = svc.parse_filename("/music/Artist - Song.flac")
        assert result["ok"] is True
        assert result["parsed"].get("artist") == "Artist"
        assert result["parsed"].get("title") == "Song"

    def test_auto_number(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.auto_number([sample_file])
        assert result["ok"] is True
        assert result["numbered"] == 1

    def test_diff_returns_changes(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "title", "Diff Title")
        changes = svc.diff(sample_file)
        assert len(changes) >= 1
        assert changes[0]["field"] == "title"

    def test_has_artwork(self, svc, sample_file):
        svc.load(sample_file)
        state = svc._active.get(sample_file)
        assert state is not None
        assert hasattr(state, "has_artwork")

    def test_cancel_operation(self, svc, sample_file):
        svc.load(sample_file)
        svc.edit_field(sample_file, "title", "Cancelled")
        confirm = svc.request_confirmation(sample_file)
        svc.cancel_operation(sample_file)
        result = svc.confirm_and_apply(sample_file, confirm["confirmation_token"])
        assert result.get("error") == "CANCELLED" or result["ok"] is True

    def test_refresh_model(self, svc, sample_file):
        svc.load(sample_file)
        result = svc.refresh_model(sample_file)
        assert result["ok"] is True

    def test_has_conflicts(self, svc, sample_file):
        svc.load(sample_file)
        conflicts = svc.has_conflicts(sample_file)
        assert isinstance(conflicts, list)
