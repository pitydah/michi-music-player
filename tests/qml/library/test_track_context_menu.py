"""Tests for track context menu actions."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
pytestmark = [pytest.mark.qml_module("library")]


class TestTrackContextMenu:
    @pytest.fixture
    def bridge(self):
        b = MagicMock()
        b.playTrackById = MagicMock(return_value={"ok": True})
        b.playNextTrackById = MagicMock(return_value={"ok": True})
        b.enqueueTrackById = MagicMock(return_value={"ok": True})
        b.toggleFavoriteById = MagicMock(return_value={"ok": True, "favorite": True})
        b.revealTrackById = MagicMock(return_value={"ok": True})
        return b

    @pytest.fixture
    def nav(self):
        n = MagicMock()
        n.navigateWithParams = MagicMock()
        n.navigate = MagicMock()
        return n

    def test_play_action(self, bridge):
        bridge.playTrackById(42)
        bridge.playTrackById.assert_called_once_with(42)

    def test_play_next_action(self, bridge):
        bridge.playNextTrackById(42)
        bridge.playNextTrackById.assert_called_once_with(42)

    def test_enqueue_action(self, bridge):
        bridge.enqueueTrackById(42)
        bridge.enqueueTrackById.assert_called_once_with(42)

    def test_replace_queue_action(self, bridge):
        bridge.playTrackById(42)
        bridge.playTrackById.assert_called_once_with(42)

    def test_favorite_toggle(self, bridge):
        result = bridge.toggleFavoriteById(42)
        assert result["ok"] is True
        bridge.toggleFavoriteById.assert_called_once_with(42)

    def test_album_navigation(self, nav):
        nav.navigateWithParams("library.album_detail", {"albumId": "Test Album"})
        nav.navigateWithParams.assert_called_once_with("library.album_detail", {"albumId": "Test Album"})

    def test_artist_navigation(self, nav):
        nav.navigateWithParams("library.artists.detail", {"artistId": "Test Artist"})
        nav.navigateWithParams.assert_called_once_with("library.artists.detail", {"artistId": "Test Artist"})

    def test_folder_reveal(self, bridge):
        bridge.revealTrackById(42)
        bridge.revealTrackById.assert_called_once_with(42)

    def test_metadata_navigation(self, nav):
        nav.navigate("metadata")
        nav.navigate.assert_called_once_with("metadata")

    def test_audio_lab_navigation(self, nav):
        nav.navigate("audio_lab")
        nav.navigate.assert_called_once_with("audio_lab")

    def test_device_navigation(self, nav):
        nav.navigate("devices")
        nav.navigate.assert_called_once_with("devices")
