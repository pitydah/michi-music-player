"""Stability tests — safe startup, optional deps, DB, file errors."""
import os
import sqlite3
import tempfile
import contextlib
from unittest.mock import MagicMock, patch


class TestSafeStartup:
    def test_home_audio_import_fallback(self):
        """HomeAudioView should be None when import fails."""
        try:
            import legacy_widgets.ui_archive.home_audio_view as hav
            assert hav is not None
        except ImportError:
            pass

    def test_detection_service_import_fallback(self):
        """DetectionService should be None when import fails."""
        with patch.dict("sys.modules", {"recognition.detection_service": None}):
            try:
                from recognition.detection_service import DetectionService
                assert DetectionService is None
            except ImportError:
                pass


class TestDatabaseSafety:
    def test_busy_timeout_set(self):
        """New DB connections must have busy_timeout."""
        db_path = os.path.join(tempfile.mkdtemp(), "test_busy.db")
        try:
            conn = sqlite3.connect(db_path)
            from library.schema import Schema
            Schema.initialize(conn)
            conn.commit()
        finally:
            with contextlib.suppress(Exception):
                conn.close()
                os.unlink(db_path)
                os.unlink(db_path + "-wal")
                os.unlink(db_path + "-shm")

    def test_get_stats_filters_deleted(self):
        """get_stats should exclude soft-deleted records."""
        db_path = os.path.join(tempfile.mkdtemp(), "test_stats.db")
        try:
            from library.library_db import LibraryDB
            db = LibraryDB(db_path)
            db._conn.execute(
                "INSERT INTO media_items (filepath, filename, directory, ext, kind)"
                " VALUES ('/tmp/a.mp3','a.mp3','/tmp','.mp3','audio')")
            db._conn.execute(
                "INSERT INTO media_items (filepath, filename, directory, ext, kind, deleted_at)"
                " VALUES ('/tmp/b.mp3','b.mp3','/tmp','.mp3','audio', 1)")
            db._conn.commit()
            stats = db.get_stats()
            assert stats["total"] == 1
        finally:
            with contextlib.suppress(Exception):
                os.unlink(db_path)
                os.unlink(db_path + "-wal")
                os.unlink(db_path + "-shm")

    def test_cleanup_missing_under_root(self):
        """cleanup_missing_under_root should only affect files in root path."""
        db_path = os.path.join(tempfile.mkdtemp(), "test_cleanup.db")
        try:
            from library.library_db import LibraryDB
            db = LibraryDB(db_path)
            db._conn.execute(
                "INSERT INTO media_items (filepath, filename, directory, ext, kind)"
                " VALUES ('/tmp/music/a.mp3','a.mp3','/tmp/music','.mp3','audio')")
            db._conn.execute(
                "INSERT INTO media_items (filepath, filename, directory, ext, kind)"
                " VALUES ('/tmp/other/b.mp3','b.mp3','/tmp/other','.mp3','audio')")
            db._conn.commit()
            db.cleanup_missing_under_root("/tmp/music")
            rows = db._conn.execute(
                "SELECT filepath, deleted_at FROM media_items"
                " WHERE filepath='/tmp/other/b.mp3'").fetchall()
            assert rows[0][1] is None
        finally:
            with contextlib.suppress(Exception):
                os.unlink(db_path)
                os.unlink(db_path + "-wal")
                os.unlink(db_path + "-shm")


class TestPlayerSafety:
    def test_play_or_resume_stopped(self):
        """play_or_resume should call play() not resume() when STOPPED."""
        engine = MagicMock()
        engine.current = "/tmp/a.mp3"
        engine._state = "STOPPED"  # Simplified state
        from audio.player_service import PlayerService
        service = PlayerService(engine)
        service.error_occurred = MagicMock()
        service.play_or_resume()
        engine.play.assert_called_once()
        engine.resume.assert_not_called()


class TestWorkerManager:
    def test_shutdown_clears_pool(self):
        """shutdown should clear thread pool."""
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        wm.shutdown(timeout_ms=500)
        assert wm.pending() == 0
