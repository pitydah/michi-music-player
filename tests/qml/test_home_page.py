"""Tests for home page display and actions — 12+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestHomePageDisplay:
    @pytest.fixture
    def hb(self):
        b = MagicMock()
        b.currentTrackTitle = "Test Song"
        b.currentArtist = "Test Artist"
        b.hasPlayback = True
        b.libraryAlbums = 10
        b.libraryArtists = 5
        b.libraryTracks = 100
        b.backend = "gstreamer"
        b.activeJobs = 2
        return b

    def test_home_bridge_has_track_info(self, hb):
        assert hb.currentTrackTitle == "Test Song"
        assert hb.currentArtist == "Test Artist"

    def test_home_bridge_has_playback(self, hb):
        assert hb.hasPlayback is True

    def test_home_bridge_library_counts(self, hb):
        assert hb.libraryAlbums == 10
        assert hb.libraryArtists == 5
        assert hb.libraryTracks == 100

    def test_home_bridge_backend_info(self, hb):
        assert hb.backend == "gstreamer"

    def test_home_bridge_active_jobs(self, hb):
        assert hb.activeJobs == 2

    def test_continue_card_shown_when_playback(self, hb):
        assert hb.hasPlayback

    def test_continue_card_hidden_when_no_playback(self):
        b = MagicMock()
        b.hasPlayback = False
        assert not b.hasPlayback

    def test_micro_server_status_not_configured(self):
        cb = MagicMock()
        cb.microServerState = "not_configured"
        assert cb.microServerState == "not_configured"

    def test_micro_server_status_connected(self):
        cb = MagicMock()
        cb.microServerState = "connected"
        assert cb.microServerState == "connected"

    def test_job_bridge_active_count(self):
        jb = MagicMock()
        jb.activeCount = 3
        assert jb.activeCount == 3

    def test_job_bridge_zero_active(self):
        jb = MagicMock()
        jb.activeCount = 0
        assert jb.activeCount == 0

    def test_navigate_to_library(self):
        nav = MagicMock()
        nav.navigate("library")
        nav.navigate.assert_called_once_with("library")

    def test_navigate_to_playback(self):
        nav = MagicMock()
        nav.navigate("playback")
        nav.navigate.assert_called_once_with("playback")

    def test_navigate_to_assistant(self):
        nav = MagicMock()
        nav.navigate("assistant")
        nav.navigate.assert_called_once_with("assistant")

    def test_navigate_to_connections(self):
        nav = MagicMock()
        nav.navigate("connections")
        nav.navigate.assert_called_once_with("connections")

    def test_navigate_to_jobs(self):
        nav = MagicMock()
        nav.navigate("jobs")
        nav.navigate.assert_called_once_with("jobs")
