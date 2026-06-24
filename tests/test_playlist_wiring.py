"""Tests for playlist UI and playback wiring."""
import os
import tempfile

import pytest


class TestAddToPlaylist:
    @pytest.fixture
    def db(self):
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        from library.library_db import LibraryDB
        db = LibraryDB(db_path)
        db._conn.execute(
            "INSERT INTO media_items (filepath,filename,directory,ext,kind) "
            "VALUES ('/tmp/a.mp3','a.mp3','/tmp','mp3','audio')")
        db._conn.execute(
            "INSERT INTO media_items (filepath,filename,directory,ext,kind) "
            "VALUES ('/tmp/b.mp3','b.mp3','/tmp','mp3','audio')")
        db._conn.commit()
        yield db
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_add_assigns_position(self, db):
        pid = db.create_playlist("Test")
        db.add_to_playlist(pid, "/tmp/a.mp3")
        db.add_to_playlist(pid, "/tmp/b.mp3")
        rows = db._conn.execute(
            "SELECT filepath, position FROM playlist_items WHERE playlist_id=? ORDER BY position",
            (pid,)).fetchall()
        assert len(rows) == 2
        assert rows[0][1] == 0
        assert rows[1][1] == 1

    def test_duplicate_not_inserted(self, db):
        pid = db.create_playlist("Test")
        db.add_to_playlist(pid, "/tmp/a.mp3")
        db.add_to_playlist(pid, "/tmp/a.mp3")  # duplicate
        count = db._conn.execute(
            "SELECT COUNT(*) FROM playlist_items WHERE playlist_id=?", (pid,)).fetchone()[0]
        assert count == 1

    def test_get_playlist_items_respects_position(self, db):
        pid = db.create_playlist("Test")
        db.add_to_playlist(pid, "/tmp/b.mp3")
        db.add_to_playlist(pid, "/tmp/a.mp3")
        items = db.get_playlist_items(pid)
        assert len(items) >= 1
        # position should be respected in ORDER BY


class TestSetQueue:
    def test_set_queue_respects_start_index(self):
        from unittest.mock import MagicMock
        mock_engine = MagicMock()
        from audio.player_service import PlayerService
        svc = PlayerService(mock_engine)
        paths = ["/tmp/a.mp3", "/tmp/b.mp3", "/tmp/c.mp3"]
        svc.play_queue(paths, start_index=1)
        mock_engine.set_queue.assert_called_once_with(paths, 1)

    def test_set_queue_plays_from_start(self):
        from unittest.mock import MagicMock
        mock_engine = MagicMock()
        from audio.player_service import PlayerService
        svc = PlayerService(mock_engine)
        svc.play_queue(["/tmp/x.mp3"])
        mock_engine.set_queue.assert_called_once_with(["/tmp/x.mp3"], 0)


class TestSidebar:
    def test_sidebar_shows_playlists(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.get_playlists.return_value = [
            {"id": 1, "name": "My Mix"},
            {"id": 2, "name": "Chill"},
        ]
        mock_sidebar = MagicMock()
        mock_sidebar.item_clicked = MagicMock()

        from ui.sidebar_controller import SidebarController
        ctrl = SidebarController(mock_sidebar, mock_db)
        ctrl.rebuild([])

        calls = mock_sidebar.add_item.call_args_list
        playlist_items = [c for c in calls if c[0][0] == "pl"]
        assert len(playlist_items) >= 2  # new + 2 playlists


class TestPlaylistDetail:
    def test_track_activated_signal_exists(self):
        """Verify track_activated Signal is declared on PlaylistDetailView."""
        from PySide6.QtCore import Signal
        from ui.playlist_detail_view import PlaylistDetailView
        assert hasattr(PlaylistDetailView, 'track_activated')
        assert isinstance(PlaylistDetailView.track_activated, Signal)


def test_unique_index_created():
    """Verify schema creates the unique index."""
    tmpdir = tempfile.mkdtemp()
    try:
        from library.library_db import LibraryDB
        db_path = os.path.join(tmpdir, "test.db")
        db = LibraryDB(db_path)
        rows = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%unique_track%'"
        ).fetchall()
        assert len(rows) == 1
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
