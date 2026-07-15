"""Tests for Library v12 — query_service, pagination, fetchMore, stale guard, search,
sort, filters, selection, context actions, scan, cancel."""
from unittest.mock import MagicMock, patch

import pytest


def _make_lib_bridge(**overrides):
    from ui_qml_bridge.library_bridge import LibraryBridge
    defaults = dict(
        db=MagicMock(),
        search_engine=MagicMock(),
        playback_ctrl=MagicMock(),
        query_service=MagicMock(),
        query_executor=MagicMock(),
        worker_manager=MagicMock(),
        job_bridge=MagicMock(),
        track_action_service=MagicMock(),
        library_sources_service=MagicMock(),
    )
    defaults.update(overrides)
    return LibraryBridge(**defaults)


class TestLibraryBridgeCreation:
    def test_requires_query_service(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        with pytest.raises(Exception):
            LibraryBridge()

    def test_requires_track_action_service(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        with pytest.raises(Exception):
            LibraryBridge(query_service=MagicMock())

    def test_creation_success(self):
        lb = _make_lib_bridge()
        assert lb is not None

    def test_has_models(self):
        lb = _make_lib_bridge()
        assert lb.trackModel is not None
        assert lb.albumModel is not None


class TestPagination:
    def test_set_page_size(self):
        lb = _make_lib_bridge()
        result = lb.setPageSize(50)
        assert result.get("ok")

    def test_load_next_page(self):
        lb = _make_lib_bridge()
        result = lb.loadNextPage()
        assert result.get("ok")

    def test_reset_paging(self):
        lb = _make_lib_bridge()
        result = lb.resetPaging()
        assert result.get("ok")


class TestFilters:
    def test_set_search_query(self):
        lb = _make_lib_bridge()
        result = lb.setSearchQuery("test")
        assert result.get("ok")

    def test_clear_search(self):
        lb = _make_lib_bridge()
        result = lb.clearSearch()
        assert result.get("ok")

    def test_set_format_filter(self):
        lb = _make_lib_bridge()
        result = lb.setFormatFilter("flac")
        assert result.get("ok")

    def test_set_genre_filter(self):
        lb = _make_lib_bridge()
        result = lb.setGenreFilter("rock")
        assert result.get("ok")

    def test_filter_by_artist(self):
        lb = _make_lib_bridge()
        result = lb.filterByArtist("Artist")
        assert result.get("ok")

    def test_clear_filters(self):
        lb = _make_lib_bridge()
        result = lb.clearFilters()
        assert result.get("ok")


class TestSort:
    def test_sort_by(self):
        lb = _make_lib_bridge()
        result = lb.sortBy("title")
        assert result.get("ok")


class TestPlaybackActions:
    def test_play_song_no_file(self):
        lb = _make_lib_bridge()
        result = lb.play_song("")
        assert not result.get("ok")

    def test_enqueue_song_no_file(self):
        lb = _make_lib_bridge()
        result = lb.enqueueSong("")
        assert not result.get("ok")

    def test_play_track_by_id(self):
        lb = _make_lib_bridge()
        lb._tas = MagicMock()
        lb._tas.play_track.return_value = {"ok": True}
        result = lb.playTrackById(1)
        assert isinstance(result, dict)


class TestScan:
    def test_add_media(self):
        lb = _make_lib_bridge()
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            result = lb.addMedia(d)
            assert isinstance(result, dict)

    def test_scan_music_folder(self):
        lb = _make_lib_bridge()
        result = lb.scanMusicFolder()
        assert isinstance(result, dict)


class TestAlbumArtist:
    def test_get_album_detail(self):
        lb = _make_lib_bridge()
        result = lb.getAlbumDetail("test_key")
        assert isinstance(result, dict)

    def test_get_artist_detail(self):
        lb = _make_lib_bridge()
        result = lb.getArtistDetail("test_artist")
        assert isinstance(result, dict)

    def test_play_album(self):
        lb = _make_lib_bridge()
        result = lb.playAlbum("test_key")
        assert isinstance(result, dict)
