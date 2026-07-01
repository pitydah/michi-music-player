"""Tests for FolderHealthService."""

import os
import tempfile
from unittest.mock import MagicMock

from library.folder_models import FolderEntry
from library.folder_health import FolderHealthService


class TestHealthScoring:
    def service(self, db=None):
        return FolderHealthService(db=db)

    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            health = self.service().analyze(tmpdir)
            assert health.exists is True
            assert health.score == 100
            assert health.status == "excellent"

    def test_nonexistent_folder(self):
        health = self.service().analyze("/nonexistent_path_xyz")
        assert health.exists is False
        assert health.score == 0
        assert health.status == "critical"

    def test_folder_with_audio_no_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in ("song.flac", "track.mp3"):
                open(os.path.join(tmpdir, f), "w").close()
            health = self.service().analyze(tmpdir)
            assert health.audio_count == 2
            assert health.indexed_audio_count == 0
            assert health.score < 100  # penalized for unindexed

    def test_folder_with_audio_fake_db(self):
        db = MagicMock()
        db.get_library_roots.return_value = []
        db.get_all_by_directory.return_value = []
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            health = self.service(db).analyze(tmpdir)
            assert health.audio_count == 1
            assert health.unindexed_audio_count == 1

    def test_folder_with_cover(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "cover.jpg"), "w").close()
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            health = self.service().analyze(tmpdir)
            assert health.missing_cover is False
            assert health.audio_count == 1

    def test_folder_without_cover_but_has_audio(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            health = self.service().analyze(tmpdir)
            assert health.missing_cover is True

    def test_mixed_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in ("song.flac", "track.mp3", "other.ogg"):
                open(os.path.join(tmpdir, f), "w").close()
            health = self.service().analyze(tmpdir)
            assert health.mixed_formats is True
            assert "FLAC" in health.formats
            assert "MP3" in health.formats

    def test_unsupported_audio(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in ("song.flac", "track.mka", "file.tak"):
                open(os.path.join(tmpdir, f), "w").close()
            health = self.service().analyze(tmpdir)
            assert health.unsupported_audio_count == 2
            assert health.audio_count == 1

    def test_score_boundaries(self):
        """Test health score computation across scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            h = self.service().analyze(tmpdir)
            assert h.score == 100

            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            h = self.service().analyze(tmpdir)
            assert h.score == 100

            h = self.service().analyze("/dev/null/nonexistent")
            assert h.score == 0

    def test_recommendations_no_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            health = self.service().analyze(tmpdir)
            recs = self.service().build_recommendations(health)
            actions = [r.action for r in recs]
            assert "scan_folder" in actions

    def test_recommendations_outside_library(self):
        db = MagicMock()
        db.get_library_roots.return_value = ["/some/other/root"]
        db.get_all_by_directory.return_value = []
        with tempfile.TemporaryDirectory() as tmpdir:
            health = self.service(db).analyze(tmpdir)
            recs = self.service(db).build_recommendations(health)
            actions = [r.action for r in recs]
            assert "add_library_root" in actions

    def test_detect_missing_metadata(self):
        entries = [
            FolderEntry(path="/a.mp3", kind="audio", title="Song", artist="", album="Album"),
            FolderEntry(path="/b.mp3", kind="audio", title="", artist="Artist", album=""),
        ]
        problems = self.service().detect_missing_metadata(entries)
        assert len(problems) == 2
        assert problems[0].problem_type == "missing_metadata"

    def test_analyze_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            entries = self.service().analyze_entries(tmpdir)
            assert len(entries) >= 2  # subfolder + audio
            kinds = [e.kind for e in entries]
            assert "folder" in kinds
            assert "audio" in kinds

    def test_mixed_formats_detection(self):
        entries = [
            FolderEntry(kind="audio", ext=".flac"),
            FolderEntry(kind="audio", ext=".mp3"),
        ]
        fmts = self.service().detect_mixed_formats(entries)
        assert "FLAC" in fmts
        assert "MP3" in fmts
        assert len(fmts) == 2
