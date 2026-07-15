from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.album_repository import AlbumRepository
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT,
        ext TEXT, kind TEXT DEFAULT 'audio',
        title TEXT, artist TEXT, album TEXT,
        albumartist TEXT DEFAULT '', album_key TEXT DEFAULT '',
        year INTEGER DEFAULT 0, genre TEXT DEFAULT '',
        duration REAL DEFAULT 0,
        disc_number INTEGER DEFAULT 0,
        track_number INTEGER DEFAULT 0,
        track_uid TEXT DEFAULT '',
        play_count INTEGER DEFAULT 0, last_played REAL,
        created_at REAL DEFAULT (strftime('%s','now')),
        deleted_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return AlbumRepository(lambda: conn)


def _insert(conn, **kw):
    cols = ["filepath", "title", "artist", "album", "albumartist",
            "album_key", "year", "genre", "duration", "disc_number", "track_number"]
    vals = [kw.get(c, "") for c in cols]
    conn.execute(
        f"INSERT INTO media_items ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        vals,
    )
    conn.commit()


class TestAlbumRepository:
    def test_empty_count(self, repo):
        assert repo.count() == 0

    def test_single_album(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Test Album", album_key="test_album", year=2020)
        assert repo.count() == 1

    def test_get_by_key(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Test Album", album_key="test_album")
        album = repo.get_by_key("test_album")
        assert album is not None
        assert album["album_title"] == "Test Album"
        assert album["track_count"] == 1

    def test_get_by_key_not_found(self, repo):
        assert repo.get_by_key("nonexistent") is None

    def test_get_page_sorted(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Alpha", album_key="alpha", year=2020)
        _insert(conn, filepath="/b.flac", title="B", artist="Y",
                album="Beta", album_key="beta", year=2021)
        albums = repo.get_page(sort="title", asc=True)
        assert len(albums) == 2
        assert albums[0]["album_title"] == "Alpha"

    def test_get_page_pagination(self, conn, repo):
        for i in range(5):
            _insert(conn, filepath=f"/{i}.flac", title=f"T{i}", artist="X",
                    album=f"Album {i}", album_key=f"album_{i}", year=2000 + i)
        albums = repo.get_page(offset=1, limit=2)
        assert len(albums) == 2

    def test_search(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Greatest Hits", album_key="greatest", year=2020)
        _insert(conn, filepath="/b.flac", title="B", artist="Y",
                album="Other", album_key="other", year=2021)
        result = repo.search("greatest")
        assert len(result) == 1
        assert result[0]["album_key"] == "greatest"

    def test_tracks_for_album(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="Track A", artist="X",
                album="Test", album_key="test", track_number=1)
        _insert(conn, filepath="/b.flac", title="Track B", artist="X",
                album="Test", album_key="test", track_number=2)
        tracks = repo.tracks_for_album("test")
        assert len(tracks) == 2
        assert tracks[0]["track_number"] == 1

    def test_multi_disc_detected(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Test", album_key="test", disc_number=1)
        _insert(conn, filepath="/b.flac", title="B", artist="X",
                album="Test", album_key="test", disc_number=2)
        assert repo.multi_disc("test") is True

    def test_multi_disc_single(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Test", album_key="test", disc_number=1)
        assert repo.multi_disc("test") is False

    def test_filter_by_year(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X",
                album="Old", album_key="old", year=1990)
        _insert(conn, filepath="/b.flac", title="B", artist="X",
                album="New", album_key="new", year=2020)
        result = repo.filter(year=2020)
        assert len(result) == 1
        assert result[0]["album_key"] == "new"
