from __future__ import annotations
"""Comprehensive tests for Sources — 10+ tests."""

from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def bridge():
    return LibraryBridge(db=MagicMock(), job_bridge=MagicMock())


class TestSourcesCompleto:
    def test_add_source_folder(self, bridge):
        with patch("pathlib.Path.is_dir", return_value=True):
            result = bridge.addFolder("/music/test")
        assert result["ok"] is True
        assert result["path"] == "/music/test"

    def test_add_source_empty(self, bridge):
        result = bridge.addFolder("")
        assert not result["ok"]

    def test_add_source_not_found(self, bridge):
        with patch("pathlib.Path.is_dir", return_value=False):
            result = bridge.addFolder("/nonexistent")
        assert not result["ok"]

    def test_scan_music_folder(self, bridge):
        bridge._job_bridge = MagicMock()
        with patch.object(bridge, 'getMusicFolder', return_value="/music"), \
             patch("pathlib.Path.is_dir", return_value=True):
            result = bridge.scanMusicFolder()
            assert result["ok"] is True

    def test_scan_music_folder_not_found(self, bridge):
        with patch.object(bridge, 'getMusicFolder', return_value="/fake"):
            result = bridge.scanMusicFolder()
            assert not result["ok"]

    def test_get_music_folder(self, bridge):
        with patch("core.settings_manager.get", side_effect=Exception):
            folder = bridge.getMusicFolder()
        assert folder is not None and len(folder) > 0

    def test_set_music_folder(self, bridge):
        with patch("pathlib.Path.is_dir", return_value=True), \
             patch("core.settings_manager.set_") as mock_set:
            result = bridge.setMusicFolder("/music/new")
            assert result["ok"] is True
            mock_set.assert_called_once()

    def test_set_music_folder_not_found(self, bridge):
        with patch("pathlib.Path.is_dir", return_value=False):
            result = bridge.setMusicFolder("/bad/path")
        assert not result["ok"]

    def test_add_media_folder(self, bridge):
        bridge._job_bridge = MagicMock()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=True):
            result = bridge.addMedia("/music/newfolder")
        assert result["ok"] is True
        assert result["type"] == "folder"

    def test_add_media_file(self, bridge):
        bridge._job_bridge = MagicMock()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=False):
            result = bridge.addMedia("/music/song.flac")
        assert result["ok"] is True
        assert result["type"] == "file"

    def test_add_media_not_found(self, bridge):
        with patch("pathlib.Path.exists", return_value=False):
            result = bridge.addMedia("/nonexistent")
        assert not result["ok"]

    def test_source_filters(self, bridge):
        result = bridge.setFormatFilter("flac")
        assert result["ok"] is True
        assert bridge._filter_format == "flac"

        result = bridge.setGenreFilter("Rock")
        assert result["ok"] is True
        assert bridge._filter_genre == "Rock"

        result = bridge.setYearFilter("2020")
        assert result["ok"] is True
        assert bridge._filter_year == "2020"

    def test_source_sort(self, bridge):
        result = bridge.sortBy("title")
        assert result["ok"] is True
        assert result["key"] == "title"
        assert bridge._sort_key == "title"
        assert result["asc"] is False

    def test_source_search(self, bridge):
        result = bridge.setSearchQuery("test")
        assert result["ok"] is True
        assert bridge._search_query == "test"

    def test_source_clear_search(self, bridge):
        bridge.setSearchQuery("test")
        bridge.clearSearch()
        assert bridge._search_query == ""
