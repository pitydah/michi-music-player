from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.library_stats_repository import LibraryStatsRepository
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT,
        ext TEXT, kind TEXT DEFAULT 'audio',
        title TEXT, artist TEXT, album TEXT,
        albumartist TEXT DEFAULT '', album_key TEXT DEFAULT '',
        year INTEGER DEFAULT 0, genre TEXT DEFAULT '',
        duration REAL DEFAULT 0, size INTEGER DEFAULT 0,
        deleted_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return LibraryStatsRepository(lambda: conn)


def _insert(conn, **kw):
    cols = ["filepath", "title", "artist", "album", "albumartist",
            "album_key", "ext", "year", "duration", "size"]
    vals = [kw.get(c, "") for c in cols]
    conn.execute(
        f"INSERT INTO media_items ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        vals,
    )
    conn.commit()


class TestLibraryStatsRepository:
    def test_empty(self, repo):
        assert repo.total_tracks() == 0
        assert repo.total_albums() == 0
        assert repo.total_artists() == 0

    def test_total_tracks(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A")
        _insert(conn, filepath="/b.flac", title="B")
        assert repo.total_tracks() == 2

    def test_total_albums(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", album="X", album_key="x")
        _insert(conn, filepath="/b.flac", title="B", album="Y", album_key="y")
        assert repo.total_albums() == 2

    def test_total_artists(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="X")
        _insert(conn, filepath="/b.flac", title="B", artist="Y")
        assert repo.total_artists() == 2

    def test_total_duration(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", duration=100.0)
        _insert(conn, filepath="/b.flac", title="B", duration=200.0)
        assert repo.total_duration() == 300.0

    def test_total_size(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", size=1000)
        _insert(conn, filepath="/b.flac", title="B", size=2000)
        assert repo.total_size() == 3000

    def test_by_format(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", ext=".flac", size=100)
        _insert(conn, filepath="/b.mp3", title="B", ext=".mp3", size=50)
        formats = repo.by_format()
        assert len(formats) == 2
        fmt_map = {f["format"]: f["count"] for f in formats}
        assert fmt_map[".flac"] == 1

    def test_by_year(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", year=2020)
        _insert(conn, filepath="/b.flac", title="B", year=2021)
        years = repo.by_year()
        assert len(years) == 2
