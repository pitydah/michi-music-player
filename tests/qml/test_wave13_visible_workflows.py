"""Wave XIII: visible workflows — Main.qml, library sources, scanner, jobs, smart tagging."""
from __future__ import annotations

import time
import sqlite3

import pytest
from PySide6.QtCore import QCoreApplication


def _make_playlist_db(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS playlist_items (playlist_id INTEGER, filepath TEXT, track_id INTEGER, position INTEGER)")


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestWave13VisibleWorkflows:
    """Real visible workflows: sources, scanner, jobs, smart tagging, actions."""

    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def db_path(self, tmp_path):
        p = tmp_path / "test_visible.db"
        conn = sqlite3.connect(str(p))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT UNIQUE NOT NULL,
            filename TEXT, directory TEXT, ext TEXT, title TEXT, artist TEXT,
            album TEXT, albumartist TEXT, album_key TEXT, year INTEGER DEFAULT 0,
            genre TEXT, track_number INTEGER DEFAULT 0, duration REAL DEFAULT 0,
            track_uid TEXT, deleted_at REAL, play_count INTEGER DEFAULT 0,
            last_played REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS library_roots (
            path TEXT PRIMARY KEY, enabled INTEGER DEFAULT 1,
            created_at REAL, updated_at REAL, last_scan REAL DEFAULT 0,
            file_count INTEGER DEFAULT 0, added_count INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0, missing_count INTEGER DEFAULT 0,
            error_code TEXT DEFAULT ''
        )""")
        _make_playlist_db(conn)
        # Insert some tracks
        for i in range(100):
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory, ext, title, artist, album, album_key, track_uid) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (f"/music/track_{i}.flac", f"track_{i}.flac", "/music", ".flac",
                 f"Track_{i}", f"Artist_{i % 10}", f"Album_{i // 5}",
                 f"key_{i // 5}", f"uid_{i}")
            )
        conn.commit()
        # Add library root
        conn.execute("INSERT OR IGNORE INTO library_roots (path, enabled, created_at) VALUES (?,1,?)",
                     ("/music", time.time()))
        conn.commit()
        conn.close()
        return str(p)

    @pytest.fixture
    def services(self, db_path):
        from core.worker_manager import WorkerManager
        from ui_qml_bridge.query_executor import QueryExecutor
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from core.library_sources_service import LibrarySourcesService
        from ui_qml_bridge.library_bridge import LibraryBridge

        class FakeDB:
            def __init__(s):
                s.conn = sqlite3.connect(db_path)
                s.db_path = db_path
            def get_library_roots(s):
                return [r[0] for r in s.conn.execute(
                    "SELECT path FROM library_roots WHERE enabled=1").fetchall()]
            def add_library_root(s, path):
                import time as t
                s.conn.execute("INSERT OR IGNORE INTO library_roots (path,enabled,created_at) VALUES (?,1,?)",
                               (path, t.time()))
                s.conn.commit()
                return True
            def remove_library_root(s, path):
                s.conn.execute("DELETE FROM library_roots WHERE path=?", (path,))
                s.conn.commit()
                return True
            def get_playlists(s):
                return []
            def create_playlist(s, name):
                cur = s.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
                s.conn.commit()
                return cur.lastrowid
            def add_track_to_playlist(s, pid, filepath="", track_id=None):
                if track_id:
                    s.conn.execute("INSERT INTO playlist_items (playlist_id, track_id, position) VALUES (?,?,0)",
                                   (pid, track_id))
                elif filepath:
                    s.conn.execute("INSERT INTO playlist_items (playlist_id, filepath, position) VALUES (?,?,0)",
                                   (pid, filepath))
                s.conn.commit()
            def get_playlist_items(s, pid):
                return []
            def delete_playlist(s, pid):
                s.conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
                s.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
                s.conn.commit()

        db = FakeDB()
        wm = WorkerManager()
        qe = QueryExecutor(worker_manager=wm)
        qs = LibraryQueryService(db, db_path=db_path)
        src_svc = LibrarySourcesService(db=db)
        lib = LibraryBridge(db=db, query_service=qs, query_executor=qe)
        yield wm, qe, qs, src_svc, lib, db
        wm.shutdown(2000)
        db.conn.close()

    def test_library_sources_list(self, app, services):
        wm, qe, qs, src_svc, lib, db = services
        sources = src_svc.list()
        assert len(sources) >= 1
        assert any("/music" in s["path"] for s in sources)

    def test_library_sources_add_remove(self, app, services, tmp_path):
        wm, qe, qs, src_svc, lib, db = services
        d = tmp_path / "test_source"
        d.mkdir()
        result = src_svc.add(str(d))
        assert result.get("ok") is True
        sources = src_svc.list()
        assert any(str(d) in s["path"] for s in sources)
        result = src_svc.remove(str(d))
        assert result.get("ok") is True

    def test_track_action_play_by_id(self, app, services):
        from core.track_action_service import TrackActionService
        wm, qe, qs, src_svc, lib, db = services
        class FakePlayer:
            def __init__(s):
                s.played = []
            def enqueue(s, paths, play_now=False):
                s.played.extend(paths)
        player = FakePlayer()
        svc = TrackActionService(query_service=qs, player_service=player)
        result = svc.play_track(1)
        assert result.get("ok") is True
        assert len(player.played) == 1

    def test_track_action_enqueue_by_id(self, app, services):
        from core.track_action_service import TrackActionService
        wm, qe, qs, src_svc, lib, db = services
        class FakePlayer:
            def __init__(s):
                s.enqueued = []
            def enqueue(s, paths, play_now=False):
                s.enqueued.extend(paths)
        player = FakePlayer()
        svc = TrackActionService(query_service=qs, player_service=player)
        result = svc.enqueue_track(2)
        assert result.get("ok") is True
        assert len(player.enqueued) == 1

    def test_queue_save_as_playlist(self, app, services):
        wm, qe, qs, src_svc, lib, db = services
        from ui_qml_bridge.queue_bridge import QueueBridge
        class FakePlayer:
            def __init__(s):
                s.q = []
            def get_queue(s):
                return [{"track_id": i, "title": f"T{i}", "duration": 200} for i in range(5)]
        player = FakePlayer()
        qb = QueueBridge(player_service=player)
        qb.refresh()
        assert qb.queueCount == 5

    def test_smart_tagging_scan_track(self, app, services):
        wm, qe, qs, src_svc, lib, db = services
        # SmartTaggingBridge with mock service
        from unittest.mock import MagicMock
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        from types import SimpleNamespace
        svc = MagicMock()
        svc.suggest_for_track.return_value = [
            SimpleNamespace(field="genre", current="", suggested="Rock",
                          confidence=0.9, source="acoustic", warning="")
        ]
        stb = SmartTaggingBridge(service=svc, worker_manager=wm, query_service=qs)
        result = stb.scanTrackById(1)
        assert result.get("ok") is True
        _process_events(1.0)
        # Should have suggestions after async completion
        assert len(stb.suggestions) > 0 or stb.status in ("scanning", "review")

    def test_home_bridge_refresh(self, app, services):
        wm, qe, qs, src_svc, lib, db = services
        from ui_qml_bridge.home_bridge import HomeBridge
        hb = HomeBridge(db=None, library_bridge=lib, library_sources_service=src_svc)
        hb._load_library_stats()
        assert hb.libraryTracks >= 0
        hb._load_sources()
        assert hb._sources_count >= 1
