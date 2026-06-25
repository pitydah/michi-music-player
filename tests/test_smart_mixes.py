"""Tests for Smart Mixes against the real schema."""
import os
import tempfile
import time

from library.smart_mixes import (
    get_popular, get_daily_mix, get_unplayed,
    get_favorites_recent, get_by_genre,
)


def _temp_db():
    """Create a temporary DB with the real schema and return its path."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "smart_mixes_test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            directory TEXT NOT NULL,
            ext TEXT NOT NULL,
            kind TEXT NOT NULL,
            play_count INTEGER DEFAULT 0,
            last_played REAL,
            genre TEXT,
            deleted_at REAL
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT NOT NULL,
            device TEXT DEFAULT 'desktop',
            played_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE,
            device TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        );
    """)
    conn.commit()
    conn.close()
    return db_path, tmpdir


def _populate(db_path):
    """Insert test data into the DB."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    now = time.time()
    yesterday = now - 86400
    last_week = now - 604800 * 2

    # Insert tracks
    tracks = [
        ("/tmp/a.mp3", "A", "Rock", 10, now - 100),
        ("/tmp/b.mp3", "B", "Rock", 5, yesterday),
        ("/tmp/c.mp3", "C", "Jazz", 0, None),
        ("/tmp/d.mp3", "D", "Pop", 0, None),
        ("/tmp/e.mp3", "E", "Rock", 3, last_week),
        ("/tmp/f.mp3", "F", "Rock", 0, None),
    ]
    for fp, title, genre, play_count, last_played in tracks:
        conn.execute(
            "INSERT INTO media_items (filepath,filename,directory,ext,kind,"
            "play_count,last_played,genre) VALUES (?,?,?,?,?,?,?,?)",
            (fp, title, "/tmp", ".mp3", "audio", play_count, last_played, genre))

    # Insert play history (track_id = filepath)
    history = [
        ("/tmp/a.mp3", yesterday),
        ("/tmp/a.mp3", now - 200),
        ("/tmp/b.mp3", yesterday),
        ("/tmp/b.mp3", now - 3600),
        ("/tmp/d.mp3", now - 7200),
    ]
    for tid, ts in history:
        conn.execute(
            "INSERT INTO play_history (track_id, played_at) VALUES (?,?)",
            (tid, ts))

    # Insert favorites
    favs = [
        ("/tmp/a.mp3", now - 500),
        ("/tmp/e.mp3", yesterday),
        ("/tmp/f.mp3", now),
    ]
    for tid, ts in favs:
        conn.execute(
            "INSERT INTO favorites (track_id, added_at) VALUES (?,?)",
            (tid, ts))

    # Soft-delete one track
    conn.execute(
        "UPDATE media_items SET deleted_at=? WHERE filepath=?",
        (now, "/tmp/f.mp3"))
    conn.commit()
    conn.close()


class TestSmartMixes:
    @classmethod
    def setup_class(cls):
        cls.db_path, cls.tmpdir = _temp_db()
        _populate(cls.db_path)

    @classmethod
    def teardown_class(cls):
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setup_method(self):
        from library.smart_mixes import DB_PATH as _orig
        self._orig_db_path = _orig
        import library.smart_mixes
        library.smart_mixes.DB_PATH = self.db_path

    def teardown_method(self):
        import library.smart_mixes
        library.smart_mixes.DB_PATH = self._orig_db_path

    def test_popular_orders_by_play_count(self):
        result = get_popular(10)
        # popular = play_count > 0: a=10, b=5, e=3 (c,d have 0; f is deleted)
        assert len(result) == 3
        assert result[0] == "/tmp/a.mp3"   # play_count=10
        assert result[1] == "/tmp/b.mp3"    # play_count=5
        assert result[2] == "/tmp/e.mp3"    # play_count=3
        assert "/tmp/f.mp3" not in result   # soft-deleted

    def test_daily_mix_uses_play_history(self):
        result = get_daily_mix(10)
        # tracks played in last 7 days: a (yesterday), b (yesterday), d (2h ago)
        # e is 2 weeks ago, excluded
        # c has no plays
        assert len(result) >= 1
        assert "/tmp/a.mp3" in result
        assert "/tmp/b.mp3" in result
        assert "/tmp/f.mp3" not in result  # soft-deleted
        # e was played 2 weeks ago, should not appear
        assert "/tmp/e.mp3" not in result

    def test_unplayed_returns_tracks_without_plays(self):
        result = get_unplayed(10)
        # c: play_count=0, no last_played → unplayed
        # d: play_count=0, no last_played → unplayed (played via play_history but
        #    media_items.play_count was never updated)
        # f: play_count=0 but soft-deleted → excluded
        # a, b, e have play_count > 0
        assert "/tmp/c.mp3" in result
        assert "/tmp/d.mp3" in result
        assert "/tmp/f.mp3" not in result
        assert "/tmp/a.mp3" not in result
        assert "/tmp/b.mp3" not in result

    def test_favorites_recent_orders_by_added_at(self):
        result = get_favorites_recent(10)
        # f is soft-deleted, excluded
        assert "/tmp/f.mp3" not in result
        # a and e are favorited and not deleted
        assert "/tmp/a.mp3" in result
        assert "/tmp/e.mp3" in result
        # Most recently added first: e (yesterday), a (now-500)
        # Actually: f (now) is deleted. a (now-500), e (yesterday)
        # Since ORDER BY added_at DESC: a should be first (added most recently among non-deleted)
        assert result[0] == "/tmp/a.mp3"

    def test_by_genre_returns_correct_genre(self):
        result = get_by_genre("Rock", 10)
        assert len(result) >= 2
        assert "/tmp/a.mp3" in result      # Rock, play_count>0
        assert "/tmp/b.mp3" in result      # Rock, play_count>0
        assert "/tmp/f.mp3" not in result  # Rock but soft-deleted
        # e is Rock too but play_count=3, should appear
        assert "/tmp/e.mp3" in result

    def test_by_genre_empty_returns_empty(self):
        result = get_by_genre("", 10)
        assert result == []

    def test_by_genre_nonexistent_returns_empty(self):
        result = get_by_genre("NonexistentGenreXYZ", 10)
        assert result == []

    def test_deleted_tracks_not_in_popular(self):
        result = get_popular(10)
        assert "/tmp/f.mp3" not in result
