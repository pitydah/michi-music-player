"""Tests for CoverFlowController — show, snap, play, queue, enrich, cover loading."""
from unittest.mock import MagicMock, patch

import pytest

from legacy_widgets.ui.controllers.legacy_controllers.coverflow_controller import _album_key, CoverFlowController


def _make_item(title="Album", subtitle="Artist · 2024 · 12 ♪", tracks_len=3):
    tracks = []
    artist = subtitle.split("·")[0].strip() if subtitle else "A"
    for i in range(tracks_len):
        t = MagicMock()
        t.filepath = f"/path/to/{title}_{i}.flac"
        t.title = f"Track {i}"
        t.artist = artist
        t.album = title
        t.albumartist = ""
        t.duration = 200.0 + i * 10
        t.year = 2024
        t.ext = ".flac"
        tracks.append(t)
    item = MagicMock()
    item.title = title
    item.subtitle = subtitle
    item.pixmap = None
    item.data = {"album": title, "artist": artist, "tracks": tracks}
    return item, tracks


class TestAlbumKey:
    def test_stable_key_from_title_and_artist(self):
        item, tracks = _make_item(title="Dark Side", subtitle="Pink Floyd · 1973 · 10 ♪")
        key1 = _album_key(item, tracks)
        key2 = _album_key(item, tracks)
        assert key1 == key2
        assert len(key1) == 16

    def test_different_albums_have_different_keys(self):
        item_a, t_a = _make_item(title="Album A", subtitle="Artist1 · 2024 · 5 ♪")
        item_b, t_b = _make_item(title="Album B", subtitle="Artist2 · 2024 · 3 ♪")
        assert _album_key(item_a, t_a) != _album_key(item_b, t_b)

    def test_key_with_no_tracks_falls_back_to_subtitle(self):
        item, _ = _make_item(tracks_len=0)
        item.subtitle = "Solo Artist"
        key1 = _album_key(item, [])
        item.subtitle = "Different Artist"
        key2 = _album_key(item, [])
        assert key1 != key2

    def test_key_normalizes_case(self):
        item_a, t_a = _make_item(title="ALBUM", subtitle="Artist · 2024")
        item_b, t_b = _make_item(title="album", subtitle="Artist · 2024")
        assert _album_key(item_a, t_a) == _album_key(item_b, t_b)


class TestCoverFlowControllerShow:
    @pytest.fixture
    def ctrl(self, qapp):
        win = MagicMock()
        win._view_switcher = MagicMock()
        win._coverflow = MagicMock()
        win._coverflow_cache_key = None
        win._albums_stack = MagicMock()
        win._count = MagicMock()
        win._views = MagicMock()
        win._fade_content = MagicMock()
        win._lib_ctrl = MagicMock()
        win._lib_ctrl.filtered_album_items = MagicMock(return_value=[])
        win._album_sort_key = "title"
        win._album_filter_mode = "all"
        win._search_text = ""
        win._artist_ctrl = MagicMock()
        win._coverflow.count = MagicMock(return_value=5)
        win._coverflow.current_index = MagicMock(return_value=2)
        return CoverFlowController(win)

    def test_cache_hit_updates_snapped_index(self, ctrl):
        ctrl._win._coverflow_cache_key = "same_key"
        with patch("ui.controllers.coverflow_controller.hashlib.sha1") as mock_sha1:
            mock_sha1.return_value.hexdigest.return_value = "same_key"
            ctrl.show()
        assert ctrl._snapped_index == 2
        ctrl._win._coverflow.setFocus.assert_called_once()

    def test_cache_miss_calls_load_covers(self, ctrl):
        ctrl._win._coverflow_cache_key = "old_key"
        with patch("ui.controllers.coverflow_controller.load_covers_for_albums") as mock_load:
            mock_load.return_value = []
            ctrl.show()
        mock_load.assert_called_once()

    def test_empty_covers_shows_empty_view(self, ctrl):
        ctrl._win._coverflow_cache_key = "old_key"
        with patch("ui.controllers.coverflow_controller.load_covers_for_albums", return_value=[]):
            ctrl.show()
        ctrl._win._views.show.assert_called_with("empty")
        ctrl._win._count.setText.assert_called_with("0 álbumes")

    def test_preserves_current_selection_across_rebuild(self, ctrl):
        ctrl._win._coverflow_cache_key = "old_key"
        ctrl._win._coverflow.current_key = MagicMock(return_value="Album|A")
        ctrl._win._coverflow.index_for_key = MagicMock(return_value=1)
        covers = [MagicMock(), MagicMock()]
        covers[0].title = "Old"
        covers[1].title = "New"
        with patch("ui.controllers.coverflow_controller.load_covers_for_albums", return_value=covers):
            ctrl.show()
        ctrl._win._coverflow.index_for_key.assert_called_with("Album|A")
        ctrl._win._coverflow.set_current_index.assert_called_with(1, animated=False)

    def test_coverflow_not_recreated_on_cache_hit(self, ctrl):
        ctrl._win._coverflow_cache_key = "same_key"
        with patch("ui.controllers.coverflow_controller.hashlib.sha1") as mock_sha1:
            mock_sha1.return_value.hexdigest.return_value = "same_key"
            ctrl.show()
            ctrl._win._coverflow.setFocus.assert_called_once()
            # set_items should NOT be called on cache hit
            ctrl._win._coverflow.set_items.assert_not_called()

    def test_show_view_delegates_to_view_switcher(self, ctrl):
        ctrl.show_view()
        ctrl._win._view_switcher.set_view.assert_called_with("coverflow", emit=False)
        ctrl._win._on_view_mode_changed.assert_called_with("coverflow")


class TestCoverFlowControllerAlbumTracks:
    @pytest.fixture
    def ctrl(self):
        win = MagicMock()
        win._coverflow = MagicMock()
        return CoverFlowController(win)

    def test_album_tracks_returns_list(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        result = ctrl.album_tracks(0)
        assert len(result) == 3

    def test_album_tracks_empty_when_no_item(self, ctrl):
        ctrl._win._coverflow.item_at = MagicMock(return_value=None)
        assert ctrl.album_tracks(0) == []

    def test_album_tracks_empty_when_no_data(self, ctrl):
        item = MagicMock()
        item.data = None
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        assert ctrl.album_tracks(0) == []


class TestCoverFlowControllerActions:
    @pytest.fixture
    def ctrl(self):
        win = MagicMock()
        win._coverflow = MagicMock()
        win._model = MagicMock()
        win._table = MagicMock()
        win._count = MagicMock()
        win._section_title = MagicMock()
        win._section_subtitle = MagicMock()
        win._fade_content = MagicMock()
        win._search = MagicMock()
        win._album_repo = MagicMock()
        win._album_banner = MagicMock()
        win._artist_enrich = MagicMock()
        win._db = MagicMock()
        win._toast_svc = MagicMock()
        win._workers = MagicMock()
        win._playback = MagicMock()
        win._album_enrich = None
        win._coverflow_cache_key = "k"
        return CoverFlowController(win)

    def test_dbl_creates_trackrefs(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.count = MagicMock(return_value=1)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl.on_dbl(0)
        assert ctrl._win._model.populate.called
        assert ctrl._win._section_title.setText.called

    def test_dbl_does_nothing_on_bad_index(self, ctrl):
        ctrl._win._coverflow.count = MagicMock(return_value=0)
        ctrl.on_dbl(5)
        ctrl._win._model.populate.assert_not_called()

    def test_dbl_does_nothing_with_no_tracks(self, ctrl):
        item, _ = _make_item(tracks_len=0)
        ctrl._win._coverflow.count = MagicMock(return_value=1)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl.on_dbl(0)
        ctrl._win._model.populate.assert_not_called()

    def test_snap_updates_banner(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.count = MagicMock(return_value=1)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl._win._album_repo.get_summary.return_value = MagicMock()
        ctrl.on_snap(0)
        ctrl._win._album_banner.set_album_summary.assert_called_once()

    def test_snap_falls_back_to_minimal_summary(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.count = MagicMock(return_value=1)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl._win._album_repo.get_summary.return_value = None
        ctrl.on_snap(0)
        ctrl._win._album_banner.set_album_summary.assert_called_once()

    def test_snap_triggers_enrichment(self, ctrl):
        item, tracks = _make_item(subtitle="Pink Floyd · 1973 · 10 ♪")
        ctrl._win._coverflow.count = MagicMock(return_value=1)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl._win._album_repo.get_summary.return_value = MagicMock()
        with patch.object(ctrl, 'enrich_album_background') as mock_enrich:
            ctrl.on_snap(0)
            mock_enrich.assert_called_once()

    def test_snap_precaches_neighbors(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.count = MagicMock(return_value=5)
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl._win._album_repo.get_summary.return_value = MagicMock()
        ctrl._win._album_repo.has = MagicMock(return_value=False)
        ctrl.on_snap(2)
        assert ctrl._win._album_repo.get_summary.call_count >= 4

    def test_play_album_calls_play_filepaths(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        with patch("os.path.isfile", return_value=True):
            ctrl.on_play_album(0)
        ctrl._win._play_filepaths.assert_called_once()

    def test_queue_album_calls_enqueue(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        with patch("os.path.isfile", return_value=True):
            ctrl.on_queue_album(0)
        ctrl._win._playback.enqueue.assert_called_once()

    def test_playlist_album_creates_playlist(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl._win._db.create_playlist.return_value = 1
        with patch("os.path.isfile", return_value=True):
            ctrl.on_playlist_album(0)
        ctrl._win._db.create_playlist.assert_called_once()
        ctrl._win._toast_svc.show.assert_called_once()

    def test_details_opens_dialog(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        with patch("ui.album_detail_dialog.AlbumDetailDialog") as mock_dlg:
            dlg = MagicMock()
            mock_dlg.return_value = dlg
            ctrl.on_details_album(0)
            mock_dlg.assert_called_once()

    def test_details_does_nothing_without_item(self, ctrl):
        ctrl._win._coverflow.item_at = MagicMock(return_value=None)
        ctrl.on_details_album(0)

    def test_metadata_calls_open_metadata(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        with patch("os.path.isfile", return_value=True):
            ctrl.on_metadata_album(0)
        ctrl._win._artist_ctrl.open_metadata_for_files.assert_called_once()

    def test_search_cover_shows_toast(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        ctrl.on_search_cover(0)
        ctrl._win._toast_svc.show.assert_called_once()

    def test_banner_play_uses_snapped_index(self, ctrl):
        ctrl._snapped_index = 3
        with patch.object(ctrl, 'on_play_album') as mock_play:
            ctrl.on_banner_play()
            mock_play.assert_called_with(3)

    def test_banner_queue_uses_snapped_index(self, ctrl):
        ctrl._snapped_index = 3
        with patch.object(ctrl, 'on_queue_album') as mock_q:
            ctrl.on_banner_queue()
            mock_q.assert_called_with(3)

    def test_banner_details_uses_snapped_index(self, ctrl):
        ctrl._snapped_index = 3
        with patch.object(ctrl, 'on_details_album') as mock_d:
            ctrl.on_banner_details()
            mock_d.assert_called_with(3)


class TestCoverFlowControllerCoverLoading:
    @pytest.fixture
    def ctrl(self):
        win = MagicMock()
        win._coverflow = MagicMock()
        win._coverflow.item_key_at.return_value = "Album|A"
        win._coverflow.cover_size.return_value = 260
        win._coverflow_cache_key = "cache_k"
        win._workers = MagicMock()
        return CoverFlowController(win)

    def test_cover_request_loads_sync(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.cover_size.return_value = 260
        with patch("ui.controllers.coverflow_controller.load_cover_pixmap") as mock_load:
            mock_load.return_value = MagicMock()
            mock_load.return_value.isNull.return_value = False
            ctrl.on_cover_request(0, item)
        mock_load.assert_called_once()
        ctrl._win._coverflow.set_cover.assert_called_once()

    def test_cover_request_dedup_by_key(self, ctrl):
        item, tracks = _make_item()
        ctrl._pending_cover_keys = {"Album|A"}
        ctrl.on_cover_request(0, item)
        ctrl._win._workers.run_task.assert_not_called()

    def test_cover_request_skip_without_tracks(self, ctrl):
        item = MagicMock()
        item.data = {"tracks": []}
        ctrl.on_cover_request(0, item)
        ctrl._win._workers.run_task.assert_not_called()

    def test_cover_request_fallback_without_workers(self, ctrl):
        ctrl._win._workers = None
        item, tracks = _make_item()
        with patch("ui.controllers.coverflow_controller.load_cover_pixmap") as mock_load:
            mock_load.return_value = MagicMock()
            mock_load.return_value.isNull.return_value = False
            ctrl.on_cover_request(0, item)
        ctrl._win._coverflow.set_cover.assert_called_once()

    def test_on_cover_loaded_updates_cover(self, ctrl):
        pix = MagicMock()
        pix.isNull.return_value = False
        ctrl._on_cover_loaded(0, pix, "Album|A", "cache_k")
        ctrl._win._coverflow.set_cover.assert_called_with(0, pix)

    def test_on_cover_loaded_discards_stale_cache(self, ctrl):
        ctrl._win._coverflow_cache_key = "new_key"
        pix = MagicMock()
        ctrl._on_cover_loaded(0, pix, "Album|A", "old_key")
        ctrl._win._coverflow.set_cover.assert_not_called()

    def test_on_cover_loaded_relocates_by_key(self, ctrl):
        ctrl._win._coverflow.item_key_at.return_value = "Other|B"
        ctrl._win._coverflow.index_for_key.return_value = 2
        pix = MagicMock()
        pix.isNull.return_value = False
        ctrl._on_cover_loaded(0, pix, "Album|A", "cache_k")
        ctrl._win._coverflow.set_cover.assert_called_with(2, pix)

    def test_on_cover_loaded_skip_null(self, ctrl):
        pix = MagicMock()
        pix.isNull.return_value = True
        ctrl._on_cover_loaded(0, pix, "Album|A", "cache_k")
        ctrl._win._coverflow.set_cover.assert_not_called()


class TestCoverFlowControllerEnrichment:
    @pytest.fixture
    def ctrl(self):
        win = MagicMock()
        win._album_repo = MagicMock()
        win._album_banner = MagicMock()
        return CoverFlowController(win)

    def test_enrich_creates_service_on_first_call(self, ctrl):
        item, tracks = _make_item()
        ctrl.enrich_album_background("key", item, tracks)
        assert ctrl._win._album_enrich is not None
        assert ctrl._win._album_enrich is not ctrl._win._album_repo

    def test_enrich_reuses_existing_service(self, ctrl):
        existing = MagicMock()
        ctrl._win._album_enrich = existing
        item, tracks = _make_item()
        ctrl.enrich_album_background("key", item, tracks)
        assert ctrl._win._album_enrich is existing

    def test_enrich_skip_without_key(self, ctrl):
        enrich_mock = MagicMock()
        ctrl._win._album_enrich = enrich_mock
        ctrl.enrich_album_background("", None, [])
        enrich_mock.enrich_album.assert_not_called()

    def test_on_album_enriched_updates_banner(self, ctrl):
        ctrl._win._album_repo.update_enrichment = MagicMock()
        ctrl._win._album_repo.get_cached.return_value = MagicMock()
        ctrl.on_album_enriched("key", {"title": "Updated"})
        ctrl._win._album_repo.update_enrichment.assert_called_with("key", {"title": "Updated"})
        ctrl._win._album_banner.set_album_summary.assert_called_once()

    def test_on_album_enriched_skip_without_repo(self, ctrl):
        del ctrl._win._album_repo
        ctrl.on_album_enriched("key", {"title": "Updated"})

    def test_on_open_folder_calls_desktop_services(self, ctrl):
        item, tracks = _make_item()
        ctrl._win._coverflow.item_at = MagicMock(return_value=item)
        with patch("ui.controllers.coverflow_controller.QDesktopServices.openUrl") as mock_open:
            ctrl.on_open_folder(0)
            mock_open.assert_called_once()

    def test_on_playlist_album_without_tracks_does_nothing(self, ctrl):
        ctrl._win._coverflow.item_at = MagicMock(return_value=None)
        ctrl.on_playlist_album(0)
        ctrl._win._db.create_playlist.assert_not_called()

    def test_selection_changed_from_coverflow(self):
        from library.coverflow import CoverFlowWidget
        from library.album_art import CoverFlowItem
        cf = CoverFlowWidget()
        results = []
        cf.selection_changed.connect(lambda i: results.append(i))
        items = [CoverFlowItem(pixmap=MagicMock(), title=f"A{i}", subtitle="T",
                               data={"album": f"A{i}", "artist": "A", "tracks": []})
                 for i in range(3)]
        cf.set_items(items)
        # scroll triggers selection_changed
        cf.scroll_to(1, animated=False)
        assert len(results) > 0
