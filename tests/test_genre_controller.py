"""Tests for GenreController — overview, detail, play, queue, metadata."""
from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.genre_controller import GenreController


@pytest.fixture
def ctx():
    c = MagicMock()
    c.genre_repo = MagicMock()
    c.genre_grid = MagicMock()
    c.genre_detail = MagicMock()
    c.metadata_editor = MagicMock()
    c.section_title = MagicMock()
    c.section_subtitle = MagicMock()
    c.view_switcher = MagicMock()
    c.show_library_hub = MagicMock()
    c.set_library_tab = MagicMock()
    c.set_genre_stack = MagicMock()
    c.fade_to = MagicMock()
    c._win = MagicMock()
    return c


@pytest.fixture
def svc():
    s = MagicMock()
    s.db = MagicMock()
    s.playback = MagicMock()
    s.toast = MagicMock()
    s.rebuild_sidebar = MagicMock()
    return s


@pytest.fixture
def ctrl(ctx, svc):
    c = GenreController.__new__(GenreController)
    c._win = ctx._win
    c._ctx = ctx
    c._svc = svc
    c._repo = svc.genre_repo if hasattr(svc, 'genre_repo') else None
    c._grid = None
    c._detail = None
    c._metadata_editor = None
    c._hub_page = None
    c._detail_page = None
    c._cleanup_page = None
    c._cleanup_ctrl = None
    c._stats_svc = None
    c._mix_svc = None
    return c


class TestGenreController:
    def test_show_genres_overview_builds_repo(self, ctrl, ctx, svc):
        svc.db.get_all.return_value = []
        ctrl.show_genres_overview()
        svc.genre_repo.build.assert_called_once()

    def test_show_genres_overview_sets_genres(self, ctrl, ctx, svc):
        svc.db.get_all.return_value = []
        ctrl.show_genres_overview()
        ctx.genre_grid.set_genres.assert_called_once()

    def test_show_genres_overview_shows_library(self, ctrl, ctx):
        ctrl.show_genres_overview()
        ctx.show_library_hub.assert_called_once()

    def test_open_genre_detail_sets_detail(self, ctrl, ctx, svc):
        g = MagicMock()
        g.name = "Rock"
        g.track_count = 50
        g.artist_count = 10
        g.album_count = 20
        svc.genre_repo.get_group.return_value = g
        svc.genre_repo.filepaths_for_genre.return_value = []
        ctrl.open_genre_detail("rock")
        ctx.genre_detail.set_genre.assert_called_with(g)
        ctx.section_title.setText.assert_called_with("Rock")
        ctx.set_genre_stack.assert_called_with(1)

    def test_open_genre_detail_not_found(self, ctrl, svc):
        svc.genre_repo.get_group.return_value = None
        ctrl.open_genre_detail("nonexistent")

    def test_back_to_overview_calls_show(self, ctrl):
        with patch.object(ctrl, 'show_genres_overview') as mock_show:
            ctrl.back_to_overview()
            mock_show.assert_called_once()

    def test_play_genre_calls_play_queue(self, ctrl, svc):
        svc.genre_repo.filepaths_for_genre.return_value = ["/a.flac", "/b.flac"]
        ctrl.play_genre("rock")
        svc.playback.play_queue.assert_called_with(["/a.flac", "/b.flac"])

    def test_play_genre_with_shuffle(self, ctrl, svc):
        svc.genre_repo.filepaths_for_genre.return_value = ["/a.flac", "/b.flac"]
        with patch("random.shuffle") as mock_shuffle:
            ctrl.play_genre("rock", shuffle=True)
            mock_shuffle.assert_called_once()

    def test_play_genre_no_files(self, ctrl, svc):
        svc.genre_repo.filepaths_for_genre.return_value = []
        ctrl.play_genre("rock")
        svc.playback.play_queue.assert_not_called()

    def test_queue_genre_calls_enqueue(self, ctrl, svc):
        svc.genre_repo.filepaths_for_genre.return_value = ["/a.flac"]
        ctrl._win._playback_ctrl = None
        ctrl.queue_genre("rock")
        svc.playback.enqueue.assert_called_with(["/a.flac"], play_now=False)

    def test_create_playlist_from_genre(self, ctrl, svc):
        g = MagicMock()
        g.name = "Rock"
        t1 = MagicMock()
        t1.filepath = "/a.flac"
        t2 = MagicMock()
        t2.filepath = "/b.flac"
        g.tracks = [t1, t2]
        svc.genre_repo.get_group.return_value = g
        svc.db.create_playlist.return_value = 1
        with patch("os.path.isfile", return_value=True):
            ctrl.create_playlist_from_genre("rock")
        svc.db.create_playlist.assert_called_with("Rock")
        svc.toast.show.assert_called_once()

    def test_edit_genre_metadata_loads_files(self, ctrl, svc):
        svc.genre_repo.filepaths_for_genre.return_value = ["/a.flac"]
        ctrl.edit_genre_metadata("rock")
        ctrl._ctx.metadata_editor.load_files.assert_called_with(["/a.flac"])

    def test_normalize_genre_shows_toast(self, ctrl, svc):
        g = MagicMock()
        g.name = "Rock"
        svc.genre_repo.get_group.return_value = g
        ctrl.normalize_genre("rock")
        svc.toast.show.assert_called_once()
