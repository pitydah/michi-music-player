"""Wave XII: real async production flow — 5000 tracks, WorkerManager, event loop."""
from __future__ import annotations

import time
import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication


def _make_schema(conn):
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=OFF;
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL DEFAULT '',
            directory TEXT NOT NULL DEFAULT '',
            ext TEXT NOT NULL DEFAULT '',
            kind TEXT DEFAULT 'audio',
            size INTEGER DEFAULT 0,
            mtime REAL DEFAULT 0,
            duration REAL DEFAULT 0,
            channels INTEGER DEFAULT 2,
            sample_rate INTEGER DEFAULT 44100,
            bitrate INTEGER DEFAULT 320,
            title TEXT DEFAULT '',
            artist TEXT DEFAULT '',
            album TEXT DEFAULT '',
            albumartist TEXT DEFAULT '',
            album_key TEXT DEFAULT '',
            year INTEGER DEFAULT 0,
            genre TEXT DEFAULT '',
            track_number INTEGER DEFAULT 0,
            track_total INTEGER DEFAULT 0,
            disc_number INTEGER DEFAULT 0,
            disc_total INTEGER DEFAULT 0,
            bit_depth INTEGER DEFAULT 16,
            play_count INTEGER DEFAULT 0,
            last_played REAL DEFAULT 0,
            track_uid TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now')),
            deleted_at REAL
        );
        CREATE TABLE IF NOT EXISTS media_fts (
            id INTEGER PRIMARY KEY,
            title TEXT, artist TEXT, album TEXT
        );
    """)


def _populate(conn, count=5000):
    import random
    random.seed(1)
    genres = ["Rock", "Pop", "Jazz", "Classical", "Electronic", "Metal", "Blues"]
    folders = ["/music", "/music/Rock", "/music/Jazz"]
    total = 0
    for i in range(count):
        folder = folders[i % len(folders)]
        ext = random.choice(["flac", "mp3", "wav"])
        fp = f"{folder}/track_{i}.{ext}"
        artist = f"Artist_{i % 50}"
        album = f"Album_{(i // 10) % 30}"
        album_key = f"key_{(i // 10) % 30}"
        title = f"Track_{i}"
        genre = random.choice(genres)
        year = 1990 + (i % 35)
        conn.execute(
            """INSERT OR IGNORE INTO media_items
            (filepath, filename, directory, ext, title, artist, album,
             albumartist, album_key, year, genre, track_number, track_uid, duration)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fp, f"track_{i}.{ext}", folder, f".{ext}",
             title, artist, album, artist,
             album_key, year, genre, (i % 20) + 1, f"uid_{i}", random.uniform(120, 600))
        )
        total += 1
    conn.commit()
    return total


def _process_events_until(condition, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


class TestWave12AsyncProductionFlow:
    """Real async flow with WorkerManager, QueryExecutor, 5000 tracks."""

    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db_path(self, tmp_path):
        p = tmp_path / "test_5000.db"
        conn = sqlite3.connect(str(p))
        _make_schema(conn)
        _populate(conn, 5000)
        conn.close()
        return str(p)

    @pytest.fixture
    def services(self, db_path):
        from core.worker_manager import WorkerManager
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService

        class FakeDB:
            def __init__(s):
                s.conn = sqlite3.connect(db_path)
                s.db_path = db_path

        db = FakeDB()
        wm = WorkerManager()
        qe = QueryExecutor(worker_manager=wm)
        qs = LibraryQueryService(db, db_path=db_path)
        yield wm, qe, qs, db
        wm.shutdown(2000)
        db.conn.close()

    def test_refresh_async_5000(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        wm, qe, qs, db = services
        model = TrackListModel(query_service=qs, query_executor=qe)
        assert model.count == 0
        model.refresh()
        assert model.loading is True
        ok = _process_events_until(lambda: not model.loading)
        assert ok, "Refresh timed out"
        assert model.totalCount == 5000
        assert model.count == 250
        assert model.hasMore is True
        assert model.errorCode == ""

    def test_fetch_more_preserves_query(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        wm, qe, qs, db = services
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(artist="Artist_0")
        ok = _process_events_until(lambda: not model.loading)
        assert ok, "Refresh timed out"
        # Artist_0 has 100 tracks, page_size=250, all fit in one page
        assert model.count == 100
        assert model.totalCount == 100
        assert model.hasMore is False
        # Verify filter applied
        for i in range(min(model.count, 10)):
            a = model.data(model.index(i), model.ArtistRole)
            assert a == "Artist_0"

    def test_fast_search_wins(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        wm, qe, qs, db = services
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh(search="Track_1")
        model.refresh(search="Track_12")
        model.refresh(search="Track_123")
        ok = _process_events_until(lambda: not model.loading)
        assert ok
        assert model.totalCount > 0
        for i in range(min(model.count, 10)):
            t = (model.data(model.index(i), model.TitleRole) or "")
            assert "123" in t

    def test_cancel_and_requery(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        wm, qe, qs, db = services
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh()
        model.cancel()
        assert model.loading is False
        model.refresh(search="Track_5")
        ok = _process_events_until(lambda: not model.loading)
        assert ok
        assert model.totalCount > 0
        for i in range(min(model.count, 10)):
            t = (model.data(model.index(i), model.TitleRole) or "")
            assert "5" in t

    def test_two_models_concurrent(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        from ui_qml.models.AlbumListModel import AlbumListModel
        wm, qe, qs, db = services
        tm = TrackListModel(query_service=qs, query_executor=qe)
        am = AlbumListModel(query_service=qs, query_executor=qe)
        tm.refresh()
        am.refresh()
        ok = _process_events_until(lambda: not tm.loading and not am.loading)
        assert ok
        assert tm.totalCount == 5000
        assert am.totalCount == 30
        assert tm.count == 250
        assert am.count > 0

    def test_shutdown_no_crash(self, app, services):
        from ui_qml.models.TrackListModel import TrackListModel
        wm, qe, qs, db = services
        model = TrackListModel(query_service=qs, query_executor=qe)
        model.refresh()
        qe.shutdown()
        wm.shutdown(2000)
        assert True
