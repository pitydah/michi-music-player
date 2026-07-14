from __future__ import annotations

import sqlite3
import time
import pytest

from core.library.repositories.track_repository import TrackRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        directory TEXT NOT NULL,
        ext TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'audio',
        size INTEGER DEFAULT 0,
        mtime REAL DEFAULT 0,
        duration REAL DEFAULT 0,
        channels INTEGER DEFAULT 0,
        sample_rate INTEGER DEFAULT 0,
        bitrate INTEGER DEFAULT 0,
        title TEXT, artist TEXT, album TEXT,
        year INTEGER DEFAULT 0, genre TEXT DEFAULT '',
        track_number INTEGER DEFAULT 0,
        composer TEXT DEFAULT '', albumartist TEXT DEFAULT '',
        disc_number INTEGER DEFAULT 0, disc_total INTEGER DEFAULT 0,
        track_total INTEGER DEFAULT 0,
        mb_track_id TEXT DEFAULT '', mb_album_id TEXT DEFAULT '',
        mb_albumartist_id TEXT DEFAULT '',
        bit_depth INTEGER DEFAULT 0, bpm INTEGER DEFAULT 0,
        isrc TEXT DEFAULT '', label TEXT DEFAULT '',
        conductor TEXT DEFAULT '', compilation INTEGER DEFAULT 0,
        media_type TEXT DEFAULT '', encoder TEXT DEFAULT '',
        copyright TEXT DEFAULT '', originaldate TEXT DEFAULT '',
        remixer TEXT DEFAULT '', grouping TEXT DEFAULT '',
        mood TEXT DEFAULT '',
        replaygain_track REAL DEFAULT 0, replaygain_album REAL DEFAULT 0,
        replaygain_track_peak REAL DEFAULT 0,
        play_count INTEGER DEFAULT 0, last_played REAL,
        rating INTEGER DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now')),
        updated_at REAL, last_scanned REAL, track_uid TEXT DEFAULT '',
        deleted_at REAL, scan_status TEXT DEFAULT 'ok',
        scan_error TEXT DEFAULT '', album_key TEXT DEFAULT '',
        content_hash TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS media_fts (
        content TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS play_history (
        track_id TEXT, played_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return TrackRepository(lambda: conn)


@pytest.fixture
def sample_tracks(conn):
    t = time.time()
    for i in range(5):
        conn.execute(
            "INSERT INTO media_items (filepath, filename, directory, ext, title, "
            "artist, album, year, genre, duration, track_uid, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"/music/track{i}.flac", f"track{i}.flac", "/music",
             ".flac", f"Track {i}", "Test Artist", "Test Album",
             2020 + i, "Rock", 200.0 + i, f"uid{i}", t),
        )
    conn.commit()


class TestTrackRepository:
    def test_get_by_id_found(self, repo, sample_tracks):
        track = repo.get_by_id(1)
        assert track is not None
        assert track["title"] == "Track 0"
        assert track["artist"] == "Test Artist"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id(999) is None

    def test_get_by_ids(self, repo, sample_tracks):
        tracks = repo.get_by_ids([1, 3])
        assert len(tracks) == 2
        assert tracks[0]["id"] == 1

    def test_get_by_ids_empty(self, repo):
        assert repo.get_by_ids([]) == []

    def test_get_page_default(self, repo, sample_tracks):
        tracks = repo.get_page()
        assert len(tracks) == 5

    def test_get_page_offset_limit(self, repo, sample_tracks):
        tracks = repo.get_page(offset=1, limit=2)
        assert len(tracks) == 2

    def test_get_page_sort(self, repo, sample_tracks):
        tracks = repo.get_page(sort="year", asc=True)
        assert tracks[0]["year"] == 2020

    def test_count(self, repo, sample_tracks):
        assert repo.count() == 5

    def test_count_empty(self, repo):
        assert repo.count() == 0

    def test_filter_by_artist(self, repo, sample_tracks):
        result = repo.filter(artist="Test Artist")
        assert len(result) == 5

    def test_filter_by_genre(self, repo, sample_tracks):
        result = repo.filter(genre="Rock")
        assert len(result) == 5

    def test_filter_by_unknown_genre(self, repo, sample_tracks):
        result = repo.filter(genre="Jazz")
        assert len(result) == 0

    def test_insert(self, repo, conn):
        track_id = repo.insert(
            filepath="/new/file.flac", filename="file.flac",
            directory="/new", ext=".flac", title="New Track",
            artist="New Artist", album="New Album",
        )
        assert track_id > 0
        row = conn.execute("SELECT title FROM media_items WHERE id=?", (track_id,)).fetchone()
        assert row[0] == "New Track"

    def test_update(self, repo, sample_tracks):
        ok = repo.update(1, title="Updated Title")
        assert ok
        track = repo.get_by_id(1)
        assert track["title"] == "Updated Title"

    def test_delete_soft(self, repo, sample_tracks):
        ok = repo.delete(1)
        assert ok
        assert repo.get_by_id(1) is None

    @pytest.mark.skipif("True")
    def test_search_fts(self, repo, sample_tracks):
        pass
