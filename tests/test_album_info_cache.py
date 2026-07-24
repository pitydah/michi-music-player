"""Tests for AlbumInfoRepository LRU cache — memory + SQLite fallback."""

from unittest.mock import patch, MagicMock

import pytest

from metadata.album_info_repository import AlbumInfoRepository
from metadata.album_summary import AlbumSummary


@pytest.fixture
def repo():
    return AlbumInfoRepository(max_size=200)


class TestAlbumInfoCache:

    def test_cache_stores_and_retrieves(self, repo):
        summary = AlbumSummary(album_key="dsotm", title="Dark Side", artist="Pink Floyd")
        repo._put("dsotm", summary)
        assert repo.has("dsotm")
        result = repo.get_summary("dsotm")
        assert result is not None
        assert result.title == "Dark Side"
        assert result.artist == "Pink Floyd"

    def test_cache_max_size_200(self, repo):
        for i in range(250):
            k = f"album_{i:03d}"
            repo._put(k, AlbumSummary(album_key=k, title=f"Album {i}"))
        assert len(repo._lru) == 200
        # First 50 should have been evicted (LRU order)
        assert not repo.has("album_000")
        assert not repo.has("album_049")
        # Last 200 should still be present
        assert repo.has("album_050")
        assert repo.has("album_249")

    def test_cache_eviction_lru(self):
        small = AlbumInfoRepository(max_size=3)
        small._put("a", AlbumSummary(album_key="a"))
        small._put("b", AlbumSummary(album_key="b"))
        small._put("c", AlbumSummary(album_key="c"))
        # Access "a" so it becomes most recent
        small.get_summary("a")
        # Add "d" — should evict "b" (least recently used after access order)
        small._put("d", AlbumSummary(album_key="d"))
        assert small.has("a")
        assert not small.has("b")
        assert small.has("c")
        assert small.has("d")

    @patch("integrations.artist_metadata.album_cache.AlbumCache")
    def test_cache_fallback_sqlite(self, MockAlbumCache):
        mock_instance = MockAlbumCache.return_value
        mock_instance.get_metadata.return_value = {
            "album_key": "cached_album",
            "title": "From SQLite",
            "artist": "Cached Artist",
            "year": "2022",
            "genre": "Electronic",
        }
        repo = AlbumInfoRepository()
        result = repo.get_summary("cached_album")
        assert result is not None
        assert result.title == "From SQLite"
        assert result.artist == "Cached Artist"
        assert result.source == "cache"
        # Should now be in LRU
        assert repo.has("cached_album")

    def test_album_without_artwork(self, repo):
        summary = AlbumSummary(
            album_key="no_cover",
            title="No Cover Album",
            artist="Some Artist",
            cover_path="",
            cover_url="",
        )
        repo._put("no_cover", summary)
        result = repo.get_summary("no_cover")
        assert result is not None
        assert result.title == "No Cover Album"
        assert result.cover_path == ""
        # No error should occur when accessing artwork-related fields
        assert result.cover_url == ""

    def test_multi_disc_album(self, repo):
        tracks = []
        for disc in (1, 2):
            for i in range(5):
                t = MagicMock()
                t.album = "Multi-Disc Album"
                t.artist = "Prog Band"
                t.albumartist = "Prog Band"
                t.duration = 300.0
                t.year = 1999
                t.genre = "Progressive Rock"
                t.filepath = f"/music/disc{disc:02d}/track{i+1:02d}.flac"
                t.disc = disc
                t.track = i + 1
                tracks.append(t)
        summary = repo._build_from_tracks("multi_disc", tracks)
        assert summary.title == "Multi-Disc Album"
        assert summary.track_count == 10
        assert summary.duration == 3000.0
        assert summary.genre == "Progressive Rock"
        assert len(summary.track_list) == 10
