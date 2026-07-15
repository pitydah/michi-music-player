from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.artist_repository import ArtistRepository
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
        duration REAL DEFAULT 0,
        disc_number INTEGER DEFAULT 0,
        track_number INTEGER DEFAULT 0,
        track_uid TEXT DEFAULT '',
        compilation INTEGER DEFAULT 0,
        play_count INTEGER DEFAULT 0, last_played REAL,
        created_at REAL DEFAULT (strftime('%s','now')),
        deleted_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return ArtistRepository(lambda: conn)


def _insert(conn, **kw):
    cols = ["filepath", "title", "artist", "album", "albumartist",
            "album_key", "year", "genre", "duration", "compilation"]
    vals = [kw.get(c, "") for c in cols]
    conn.execute(
        f"INSERT INTO media_items ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        vals,
    )
    conn.commit()


class TestArtistRepository:
    def test_empty_count(self, repo):
        assert repo.count() == 0

    def test_count(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Artist X",
                album="Album", album_key="album_x")
        _insert(conn, filepath="/b.flac", title="B", artist="Artist Y",
                album="Album2", album_key="album_y")
        assert repo.count() == 2

    def test_get_by_name(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Artist X",
                album="Album", album_key="album_x")
        artist = repo.get_by_name("Artist X")
        assert artist is not None
        assert artist["track_count"] == 1

    def test_get_by_name_not_found(self, repo):
        assert repo.get_by_name("Nadie") is None

    def test_get_page(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Alpha",
                album="A1", album_key="a1")
        _insert(conn, filepath="/b.flac", title="B", artist="Beta",
                album="B1", album_key="b1")
        artists = repo.get_page(sort="name", asc=True)
        assert len(artists) == 2
        assert artists[0]["artist_name"] == "Alpha"

    def test_get_page_pagination(self, conn, repo):
        for i in range(5):
            _insert(conn, filepath=f"/{i}.flac", title=f"T{i}",
                    artist=f"Artist {i}", album=f"A{i}", album_key=f"a{i}")
        artists = repo.get_page(offset=1, limit=2)
        assert len(artists) == 2

    def test_search(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Metallica",
                album="Master", album_key="master")
        _insert(conn, filepath="/b.flac", title="B", artist="Megadeth",
                album="Rust", album_key="rust")
        result = repo.search("Metallica")
        assert len(result) == 1

    def test_albums_for_artist(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Artist X",
                album="Album 1", album_key="a1")
        _insert(conn, filepath="/b.flac", title="B", artist="Artist X",
                album="Album 2", album_key="a2")
        albums = repo.albums_for_artist("Artist X")
        assert len(albums) == 2

    def test_tracks_for_artist(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Artist X",
                album="Album", album_key="album_x")
        _insert(conn, filepath="/b.flac", title="B", artist="Artist X",
                album="Album", album_key="album_x")
        tracks = repo.tracks_for_artist("Artist X")
        assert len(tracks) == 2

    def test_compilations(self, conn, repo):
        _insert(conn, filepath="/a.flac", title="A", artist="Artist X",
                album="Comp", album_key="comp", compilation=1)
        comps = repo.compilations("Artist X")
        assert len(comps) == 1
