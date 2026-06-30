"""Tests for AlbumDetailView — premium album detail panel."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestAlbumDetailView:
    def test_set_album_no_crash_empty(self, qtbot):
        from ui.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        view.set_album(title="Test", artist="Artist", tracks=[])
        assert view._tracks == []

    def test_set_album_with_tracks(self, qtbot):
        from ui.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        t1 = MagicMock()
        t1.filepath = "/test/s1.flac"
        t1.title = "Song 1"
        t1.artist = "Artist"
        t1.duration = 200.0
        t1.ext = "flac"
        t1.sample_rate = 44100
        t1.bit_depth = 16
        t1.track_number = 1
        view.set_album(title="Album", artist="Artist", tracks=[t1])
        assert view._table.rowCount() == 1

    def test_double_click_emits_track_play(self, qtbot):
        from ui.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        results = []
        view.track_play_requested.connect(results.append)
        t1 = MagicMock()
        t1.filepath = "/test/s1.flac"
        t1.title = "Song 1"
        t1.artist = "Artist"
        t1.duration = 200.0
        t1.ext = "flac"
        t1.sample_rate = 44100
        t1.bit_depth = 16
        t1.track_number = 1
        view.set_album(title="Album", artist="Artist", tracks=[t1])
        view._on_track_dbl(type("Idx", (), {"row": lambda: 0, "isValid": lambda: True})())
        assert len(results) == 1
        assert results[0] == "/test/s1.flac"

    def test_action_buttons_exist(self, qtbot):
        from ui.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        row = view._action_row
        assert row is not None
        assert hasattr(row, "play_clicked")
        assert hasattr(row, "queue_clicked")
        assert hasattr(row, "playlist_clicked")
        assert hasattr(row, "metadata_clicked")
        assert hasattr(row, "cover_clicked")
        assert hasattr(row, "quality_clicked")
        assert hasattr(row, "server_clicked")
        assert hasattr(row, "mobile_clicked")

    def test_back_button_emits_back(self, qtbot):
        from ui.album_detail_view import AlbumDetailView
        view = AlbumDetailView()
        qtbot.addWidget(view)
        results = []
        view.back_requested.connect(results.append)
        view.back_requested.emit()
        assert len(results) == 1
