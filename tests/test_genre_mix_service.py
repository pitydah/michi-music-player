"""Tests for GenreMixService — mix creation, radio, smart playlists."""
from unittest.mock import MagicMock, patch, call
import pytest

from core.genre.genre_mix_service import GenreMixService


class MockItem:
    def __init__(self, title="", artist="", genre="", filepath="",
                 ext=".flac", duration=200.0, sample_rate=44100,
                 bit_depth=16, bitrate=320, play_count=0, rating=0,
                 year=2020, last_played=0.0, album="Album"):
        self.title = title or "Track"
        self.artist = artist or "Artist"
        self.genre = genre
        self.filepath = filepath or f"/path/{title}.flac"
        self.ext = ext
        self.duration = duration
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.bitrate = bitrate
        self.play_count = play_count
        self.rating = rating
        self.year = year
        self.last_played = last_played
        self.album = album


@pytest.fixture
def svc():
    db = MagicMock()
    repo = MagicMock()
    return GenreMixService(db, repo)


class TestCreateMix:
    def test_all_mode(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="Track 1", filepath="/a.flac"),
            MockItem(title="Track 2", filepath="/b.flac"),
        ]
        result = svc.create_mix("Rock", mode="all", limit=10)
        assert len(result) == 2

    def test_unplayed_mode(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2, 3]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="Played", filepath="/a.flac", play_count=5),
            MockItem(title="Unplayed", filepath="/b.flac", play_count=0),
            MockItem(title="Also Unplayed", filepath="/c.flac", play_count=0),
        ]
        result = svc.create_mix("Rock", mode="unplayed", limit=10)
        assert len(result) == 2

    def test_empty_genre(self, svc):
        svc._repo.get_tracks_for_genre.return_value = []
        result = svc.create_mix("Nonexistent", mode="all")
        assert result == []

    def test_high_quality_filter(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="HQ", filepath="/a.flac", sample_rate=96000, bit_depth=24),
            MockItem(title="LQ", filepath="/b.mp3", ext=".mp3", bitrate=128,
                     sample_rate=22050, bit_depth=8),
        ]
        result = svc.create_mix("Rock", mode="high_quality", limit=10)
        assert len(result) == 1

    def test_limit_respected(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2, 3, 4, 5]
        items = [MockItem(title=f"Track {i}", filepath=f"/{i}.flac") for i in range(5)]
        db.get_media_item_by_id.side_effect = items
        result = svc.create_mix("Rock", mode="all", limit=3)
        assert len(result) == 3

    def test_artist_variety(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2, 3, 4]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="A1", filepath="/a1.flac", artist="Artist A"),
            MockItem(title="A2", filepath="/a2.flac", artist="Artist A"),
            MockItem(title="B1", filepath="/b1.flac", artist="Artist B"),
            MockItem(title="B2", filepath="/b2.flac", artist="Artist B"),
        ]
        result = svc.create_mix("Rock", mode="artist_variety", limit=4)
        assert len(result) >= 2


class TestCreateRadioQueue:
    def test_returns_queue(self, svc):
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="Track 1", filepath="/a.flac"),
            MockItem(title="Track 2", filepath="/b.flac"),
        ]
        queue = svc.create_radio_queue("Rock", initial_size=5)
        assert len(queue) >= 1

    def test_empty_genre(self, svc):
        svc._repo.get_tracks_for_genre.return_value = []
        queue = svc.create_radio_queue("Nonexistent")
        assert queue == []


class TestCreateSmartPlaylist:
    def test_creates_playlist(self, svc):
        playlist_store_called = []
        svc._playlist_store = lambda name: (
            playlist_store_called.append(name) or 1
        )
        repo = svc._repo
        db = svc._db
        repo.get_tracks_for_genre.return_value = [1, 2]
        db.get_media_item_by_id.side_effect = [
            MockItem(title="Track 1", filepath="/a.flac"),
            MockItem(title="Track 2", filepath="/b.flac"),
        ]
        pid = svc.create_smart_playlist("My Playlist", "Rock")
        assert pid is not None
        assert len(playlist_store_called) == 1

    def test_no_playlist_store(self, svc):
        svc._playlist_store = None
        pid = svc.create_smart_playlist("Test", "Rock")
        assert pid is None

    def test_empty_genre(self, svc):
        svc._playlist_store = lambda name: 1
        svc._repo.get_tracks_for_genre.return_value = []
        pid = svc.create_smart_playlist("Test", "Empty")
        assert pid is None


class TestRelatedGenres:
    def test_finds_related(self, svc):
        repo = svc._repo
        repo.get_tracks_for_genre.return_value = [1, 2]
        repo.get_track_genres.side_effect = [
            [{"canonical_genre": "Rock"}, {"canonical_genre": "Pop"}],
            [{"canonical_genre": "Rock"}, {"canonical_genre": "Jazz"}],
        ]
        related = svc.get_related_genres("Rock")
        assert len(related) >= 2


class TestSmartPlaylistRules:
    def test_apply_min_year(self, svc):
        tracks = [
            MockItem(title="Old", year=1990),
            MockItem(title="New", year=2020),
        ]
        rules = {"min_year": 2000}
        filtered = svc._apply_rules(tracks, rules)
        assert len(filtered) == 1
        assert filtered[0].title == "New"

    def test_apply_only_favorites(self, svc):
        tracks = [
            MockItem(title="Fav", rating=5),
            MockItem(title="Not Fav", rating=1),
        ]
        rules = {"only_favorites": True}
        filtered = svc._apply_rules(tracks, rules)
        assert len(filtered) == 1
        assert filtered[0].title == "Fav"

    def test_apply_exclude_format(self, svc):
        tracks = [
            MockItem(title="FLAC", ext=".flac"),
            MockItem(title="MP3", ext=".mp3"),
        ]
        rules = {"exclude_format": [".mp3"]}
        filtered = svc._apply_rules(tracks, rules)
        assert len(filtered) == 1
        assert filtered[0].title == "FLAC"

    def test_apply_max_tracks(self, svc):
        tracks = [MockItem(title=f"T{i}") for i in range(10)]
        rules = {"max_tracks": 3}
        filtered = svc._apply_rules(tracks, rules)
        assert len(filtered) == 3

    def test_apply_include_artist(self, svc):
        tracks = [
            MockItem(title="A", artist="Target Artist"),
            MockItem(title="B", artist="Other Artist"),
        ]
        rules = {"include_artist": "Target"}
        filtered = svc._apply_rules(tracks, rules)
        assert len(filtered) == 1
