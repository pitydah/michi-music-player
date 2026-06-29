"""Tests for SmartMixController — show_smart_mix, favs, recent, resolve_track_ids."""
from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.smart_mix_controller import SmartMixController


@pytest.fixture
def win():
    w = MagicMock()
    w._section_title = MagicMock()
    w._model = MagicMock()
    w._current_refs = []
    w._count = MagicMock()
    w._playlist_refs = []
    w._fade_content = MagicMock()
    w._table = MagicMock()
    w._views = MagicMock()
    w._toast_svc = MagicMock()
    w._show_expanded = MagicMock()
    w._play_filepaths = MagicMock()
    w._items_index = {}
    w._all_items = []
    w._db = MagicMock()
    w._search = MagicMock()
    return w


@pytest.fixture
def ctrl(win):
    return SmartMixController(win)


class TestSmartMixController:
    def test_show_smart_mix_daily(self, ctrl, win):
        """Show should display list, not auto-play."""
        with patch("library.smart_mixes.get_daily_mix") as mock_mix:
            mock_mix.return_value = ["/path/to/song.flac"]
            with patch("os.path.isfile", return_value=True):
                ctrl.show_smart_mix("mix_daily")
        win._section_title.setText.assert_called()
        win._play_filepaths.assert_not_called()
        win._model.populate.assert_called()

    def test_show_smart_mix_unplayed(self, ctrl, win):
        items = []
        for i in range(3):
            item = MagicMock()
            item.filepath = f"/path/song{i}.flac"
            item.title = f"Song {i}"
            item.artist = "Artist"
            item.album = "Album"
            item.duration = 200.0
            item.year = 2024
            item.genre = "Rock"
            items.append(item)
        win._items_index = {item.filepath: item for item in items}
        with patch("library.smart_mixes.get_unplayed") as mock_mix:
            mock_mix.return_value = [item.filepath for item in items]
            with patch("os.path.isfile", return_value=True):
                ctrl.show_smart_mix("mix_unplayed")
        win._model.populate.assert_called_once()
        win._count.setText.assert_called()

    def test_show_smart_mix_empty(self, ctrl, win):
        with patch("library.smart_mixes.get_unplayed") as mock_mix:
            mock_mix.return_value = []
            ctrl.show_smart_mix("mix_unplayed")
        win._views.show.assert_called_with("empty")

    def test_show_smart_mix_no_files(self, ctrl, win):
        """Show with no real files should show empty state."""
        with patch("library.smart_mixes.get_daily_mix") as mock_mix:
            mock_mix.return_value = ["/nonexistent/file.flac"]
            with patch("os.path.isfile", return_value=False):
                ctrl.show_smart_mix("mix_daily")
        win._views.show.assert_called_with("empty")

    def test_show_favs_populates_table(self, ctrl, win):
        fav = MagicMock()
        fav.filepath = "/fav/song.flac"
        fav.title = "Fav Song"
        fav.artist = "Fav Artist"
        fav.album = "Fav Album"
        fav.duration = 180.0
        fav.year = 2023
        fav.genre = "Pop"
        win._db.get_favorites.return_value = ["/fav/song.flac"]
        with patch.object(ctrl, 'resolve_track_ids', return_value=[fav]):
            ctrl.show_favs("favs")
        win._model.populate.assert_called_once()
        win._table.setModel.assert_called_once()

    def test_show_favs_empty_shows_empty_view(self, ctrl, win):
        win._db.get_favorites.return_value = []
        with patch.object(ctrl, 'resolve_track_ids', return_value=[]):
            ctrl.show_favs("favs")
        win._views.show.assert_called_with("empty")

    def test_show_recent_populates_table(self, ctrl, win):
        recent_item = MagicMock()
        recent_item.filepath = "/recent/song.flac"
        recent_item.title = "Recent Song"
        win._db.get_play_history.return_value = [{"track_id": "/recent/song.flac"}]
        with patch.object(ctrl, 'resolve_track_ids', return_value=[recent_item]):
            ctrl.show_recent("recent")
        win._model.populate.assert_called_once()

    def test_show_recent_empty(self, ctrl, win):
        win._db.get_play_history.return_value = []
        with patch.object(ctrl, 'resolve_track_ids', return_value=[]):
            ctrl.show_recent("recent")
        win._views.show.assert_called_with("empty")

    def test_resolve_track_ids_by_filepath(self, ctrl, win):
        item = MagicMock()
        item.filepath = "/path/to/song.flac"
        item.id = 1
        item.track_uid = ""
        win._all_items = [item]
        win._items_index = {item.filepath: item}
        result = ctrl.resolve_track_ids(["/path/to/song.flac"])
        assert len(result) == 1
        assert result[0] is item

    def test_resolve_track_ids_deduplicates(self, ctrl, win):
        item = MagicMock()
        item.filepath = "/song.flac"
        item.id = 1
        item.track_uid = ""
        win._all_items = [item]
        win._items_index = {item.filepath: item}
        result = ctrl.resolve_track_ids(["/song.flac", "/song.flac"])
        assert len(result) == 1

    def test_resolve_track_ids_loads_all_items_if_needed(self, ctrl, win):
        win._all_items = []
        win._db.get_all.return_value = []
        result = ctrl.resolve_track_ids(["nonexistent"])
        assert result == []

    def test_show_smart_mix_popular(self, ctrl, win):
        """Show should display list, not auto-play."""
        with patch("library.smart_mixes.get_popular") as mock_mix:
            mock_mix.return_value = ["/popular/song.flac"]
            with patch("os.path.isfile", return_value=True):
                ctrl.show_smart_mix("mix_popular")
        win._play_filepaths.assert_not_called()
        win._model.populate.assert_called()

    def test_show_smart_mix_unknown_key_sets_title(self, ctrl, win):
        ctrl.show_smart_mix("mix_unknown")
        win._section_title.setText.assert_called()
