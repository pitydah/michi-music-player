"""Tests for GenreCleanupService — detection, suggestions, execution."""
from unittest.mock import MagicMock, patch
import pytest

from core.genre.genre_cleanup_service import GenreCleanupService


class MockItem:
    def __init__(self, genre="", id=0, filepath="", title="",
                 artist="", album="", ext=".flac", duration=200.0,
                 sample_rate=44100, bit_depth=16, play_count=0, rating=0):
        self.id = id
        self.filepath = filepath or f"/path/{title}.flac"
        self.title = title or f"Track {id}"
        self.artist = artist or "Artist"
        self.album = album or "Album"
        self.genre = genre
        self.ext = ext
        self.duration = duration
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.play_count = play_count
        self.rating = rating


@pytest.fixture
def svc():
    db = MagicMock()
    repo = MagicMock()
    return GenreCleanupService(db, repo)


class TestDetectDuplicates:
    def test_no_duplicates(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock"),
            MockItem(genre="Pop"),
            MockItem(genre="Jazz"),
        ]
        dups = svc.detect_duplicates()
        assert len(dups) == 0

    def test_detects_hiphop_variants(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Hip-Hop"),
            MockItem(genre="hiphop"),
            MockItem(genre="Hip Hop"),
        ]
        dups = svc.detect_duplicates()
        assert len(dups) >= 1


class TestDetectJunk:
    def test_detects_unknown(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="unknown"),
            MockItem(genre="Rock"),
        ]
        junk = svc.detect_junk()
        assert len(junk) >= 1
        assert any(j["value"] == "unknown" for j in junk)

    def test_rock_not_junk(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock"),
            MockItem(genre="Pop"),
        ]
        junk = svc.detect_junk()
        assert len(junk) == 0


class TestDetectUntagged:
    def test_detects_empty(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre=""),
            MockItem(genre="Rock"),
        ]
        result = svc.detect_untagged()
        assert result["count"] == 1

    def test_no_untagged(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock"),
            MockItem(genre="Pop"),
        ]
        result = svc.detect_untagged()
        assert result["count"] == 0


class TestDetectRare:
    def test_rare_genres(self, svc):
        svc._repo.get_cached_stats.return_value = {
            "Rara": {"track_count": 1, "album_count": 1, "artist_count": 1, "duration_total": 200},
            "Rock": {"track_count": 50, "album_count": 5, "artist_count": 3, "duration_total": 10000},
        }
        rare = svc.detect_rare_genres(min_tracks=3)
        assert len(rare) == 1
        assert rare[0]["genre"] == "Rara"

    def test_no_rare(self, svc):
        svc._repo.get_cached_stats.return_value = {
            "Rock": {"track_count": 10, "album_count": 1, "artist_count": 1, "duration_total": 2000},
        }
        rare = svc.detect_rare_genres(min_tracks=3)
        assert len(rare) == 0


class TestDetectMultiGenre:
    def test_detects_multi(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock, Pop", id=1, title="Multi Song"),
            MockItem(genre="Rock", id=2, title="Single"),
        ]
        issues = svc.detect_multi_genre_issues()
        assert len(issues) == 1
        assert issues[0]["track_id"] == 1

    def test_no_multi(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock"),
            MockItem(genre="Pop"),
        ]
        issues = svc.detect_multi_genre_issues()
        assert len(issues) == 0


class TestExecute:
    def test_execute_merge(self, svc):
        svc._repo.merge_genres.return_value = {"affected": 10, "track_ids": [1, 2, 3]}
        result = svc.execute_merge(["Old"], "New")
        assert result["affected"] == 10

    def test_execute_rename(self, svc):
        svc._repo.rename_genre.return_value = 5
        result = svc.execute_rename("Old", "New")
        assert result == 5

    def test_execute_apply_genre(self, svc):
        svc._repo.apply_genre_to_tracks.return_value = 3
        result = svc.execute_apply_genre([1, 2, 3], "Rock")
        assert result == 3


class TestDetectInconsistentAlbums:
    def test_detects_inconsistent(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock", album="Mixed Album"),
            MockItem(genre="Pop", album="Mixed Album"),
        ]
        issues = svc.detect_inconsistent_albums()
        assert len(issues) == 1

    def test_consistent_album(self, svc):
        svc._db.get_all.return_value = [
            MockItem(genre="Rock", album="Rock Album"),
            MockItem(genre="Rock", album="Rock Album"),
        ]
        issues = svc.detect_inconsistent_albums()
        assert len(issues) == 0
