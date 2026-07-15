from __future__ import annotations
"""Tests for source management workflow — 8+ tests."""

from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def bridge():
    return LibraryBridge(db=MagicMock(), job_bridge=MagicMock())


def test_add_folder(bridge):
    with patch("pathlib.Path.is_dir", return_value=True):
        result = bridge.addFolder("/music/test")
    assert result["ok"] is True
    assert result["path"] == "/music/test"


def test_add_folder_empty(bridge):
    result = bridge.addFolder("")
    assert not result["ok"]


def test_add_folder_not_found(bridge):
    with patch("pathlib.Path.is_dir", return_value=False):
        result = bridge.addFolder("/nonexistent")
    assert not result["ok"]


def test_get_music_folder_default(bridge):
    with patch("core.settings_manager.get", side_effect=Exception):
        folder = bridge.getMusicFolder()
    assert folder == "/home/cristian/Música" or "Música" in folder


def test_set_music_folder(bridge):
    with patch("pathlib.Path.is_dir", return_value=True), \
         patch("core.settings_manager.set_") as mock_set:
        result = bridge.setMusicFolder("/music/new")
        assert result["ok"] is True
        mock_set.assert_called_once()


def test_set_music_folder_not_found(bridge):
    with patch("pathlib.Path.is_dir", return_value=False):
        result = bridge.setMusicFolder("/bad/path")
    assert not result["ok"]


def test_scan_music_folder(bridge):
    bridge._job_bridge = MagicMock()
    with patch.object(bridge, 'getMusicFolder', return_value="/music"), \
         patch("pathlib.Path.is_dir", return_value=True):
        result = bridge.scanMusicFolder()
        assert result["ok"] is True


def test_add_media_folder(bridge):
    bridge._job_bridge = MagicMock()
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=True):
        result = bridge.addMedia("/music/newfolder")
    assert result["ok"] is True
    assert result["type"] == "folder"


def test_add_media_file(bridge):
    bridge._job_bridge = MagicMock()
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.is_dir", return_value=False):
        result = bridge.addMedia("/music/song.flac")
    assert result["ok"] is True


def test_add_media_not_found(bridge):
    with patch("pathlib.Path.exists", return_value=False):
        result = bridge.addMedia("/nonexistent")
    assert not result["ok"]


def test_source_filters(bridge):
    result = bridge.setFormatFilter("flac")
    assert result["ok"] is True
    assert bridge._filter_format == "flac"

    result = bridge.setGenreFilter("Rock")
    assert result["ok"] is True
    assert bridge._filter_genre == "Rock"

    result = bridge.setYearFilter("2020")
    assert result["ok"] is True
    assert bridge._filter_year == "2020"
