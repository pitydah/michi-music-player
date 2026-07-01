"""Tests for folder_models — pure dataclass construction and defaults."""

import os
import tempfile

from library.folder_models import (
    FolderEntry, FolderHealth, FolderProblem, FolderIntegrityResult,
    FolderDbDiff, FolderActionRecommendation, FolderMovePlan, FolderMoveResult,
    classify_status, HEALTH_EXCELLENT, HEALTH_GOOD, HEALTH_ATTENTION,
    HEALTH_WARNING, HEALTH_CRITICAL,
)


class TestFolderEntry:
    def test_defaults(self):
        e = FolderEntry()
        assert e.path == ""
        assert e.kind == "unknown"
        assert e.is_hidden is False
        assert e.is_supported_audio is False
        assert e.is_indexed is False
        assert e.problems == []

    def test_from_path_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            e = FolderEntry.from_path(tmp)
            assert e.path == tmp
            assert e.name == os.path.basename(tmp)
            assert e.is_hidden is False
            assert e.mtime > 0
        finally:
            os.unlink(tmp)

    def test_from_path_hidden(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", prefix=".", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            e = FolderEntry.from_path(tmp)
            assert e.is_hidden is True
        finally:
            os.unlink(tmp)

    def test_from_path_missing(self):
        e = FolderEntry.from_path("/nonexistent/path.mp3")
        assert e.is_hidden is False
        assert e.size == 0
        assert e.mtime == 0.0

    def test_to_dict(self):
        e = FolderEntry(path="/music/track.flac", name="track.flac", kind="audio",
                        ext=".flac", is_supported_audio=True, is_indexed=True,
                        db_id=42, duration=180.0, title="Song", artist="Artist")
        d = e.to_dict()
        assert d["path"] == "/music/track.flac"
        assert d["kind"] == "audio"
        assert d["db_id"] == 42
        assert d["is_indexed"] is True


class TestFolderHealth:
    def test_defaults(self):
        h = FolderHealth()
        assert h.score == 0
        assert h.status == HEALTH_CRITICAL
        assert h.exists is False
        assert h.recommended_actions == []

    def test_excellent_status(self):
        h = FolderHealth(score=95)
        assert classify_status(h.score) == HEALTH_EXCELLENT

    def test_good_status(self):
        h = FolderHealth(score=80)
        assert classify_status(h.score) == HEALTH_GOOD

    def test_attention_status(self):
        h = FolderHealth(score=60)
        assert classify_status(h.score) == HEALTH_ATTENTION

    def test_warning_status(self):
        h = FolderHealth(score=40)
        assert classify_status(h.score) == HEALTH_WARNING

    def test_critical_status(self):
        h = FolderHealth(score=15)
        assert classify_status(h.score) == HEALTH_CRITICAL

    def test_score_boundaries(self):
        assert classify_status(100) == HEALTH_EXCELLENT
        assert classify_status(90) == HEALTH_EXCELLENT
        assert classify_status(89) == HEALTH_GOOD
        assert classify_status(75) == HEALTH_GOOD
        assert classify_status(74) == HEALTH_ATTENTION
        assert classify_status(55) == HEALTH_ATTENTION
        assert classify_status(54) == HEALTH_WARNING
        assert classify_status(30) == HEALTH_WARNING
        assert classify_status(29) == HEALTH_CRITICAL
        assert classify_status(0) == HEALTH_CRITICAL

    def test_to_dict(self):
        h = FolderHealth(path="/music", score=85, exists=True, audio_count=10,
                         warnings=["test"])
        d = h.to_dict()
        assert d["path"] == "/music"
        assert d["score"] == 85
        assert d["warnings"] == ["test"]


class TestFolderProblem:
    def test_defaults(self):
        p = FolderProblem()
        assert p.problem_type == ""
        assert p.severity == "info"


class TestFolderIntegrityResult:
    def test_passed_true(self):
        r = FolderIntegrityResult()
        assert r.passed is True

    def test_passed_false_errors(self):
        r = FolderIntegrityResult(errors=["fail"])
        assert r.passed is False

    def test_passed_false_corrupted(self):
        r = FolderIntegrityResult(corrupted_files=["/x.mp3"])
        assert r.passed is False


class TestFolderDbDiff:
    def test_no_differences(self):
        d = FolderDbDiff()
        assert d.has_differences is False

    def test_has_differences(self):
        d = FolderDbDiff(in_fs_not_db=["/new.mp3"])
        assert d.has_differences is True


class TestFolderActionRecommendation:
    def test_defaults(self):
        a = FolderActionRecommendation()
        assert a.action == ""
        assert a.requires_confirmation is False


class TestFolderMovePlan:
    def test_defaults(self):
        p = FolderMovePlan()
        assert p.can_proceed is False
        assert p.is_rename is False


class TestFolderMoveResult:
    def test_defaults(self):
        r = FolderMoveResult()
        assert r.success is False
        assert r.rollback_performed is False
