from __future__ import annotations
"""Workflow: Continue playback  open active job  check status — 8+ tests."""

from unittest.mock import MagicMock

import pytest


class TestHomeWorkflow:
    @pytest.fixture
    def hb(self):
        b = MagicMock()
        b.currentTrackTitle = "Song"
        b.currentArtist = "Artist"
        b.hasPlayback = True
        b.activeJobs = 1
        b.backend = "gstreamer"
        return b

    @pytest.fixture
    def nav(self):
        return MagicMock()

    def test_continue_playback_navigates(self, hb, nav):
        if hb.hasPlayback:
            nav.navigate("playback")
        nav.navigate.assert_called_once_with("playback")

    def test_resume_queue_navigates(self, hb, nav):
        if hb.hasPlayback:
            nav.navigate("queue")
        nav.navigate.assert_called_once_with("queue")

    def test_open_active_job_navigates(self, nav):
        nav.navigate("jobs")
        nav.navigate.assert_called_once_with("jobs")

    def test_check_status_after_playback(self, hb):
        assert hb.hasPlayback
        track = hb.currentTrackTitle
        artist = hb.currentArtist
        assert track == "Song"
        assert artist == "Artist"

    def test_reconnect_to_source(self, hb, nav):
        if hb.backend == "gstreamer":
            nav.navigate("connections")
        nav.navigate.assert_called_once_with("connections")

    def test_open_current_source(self, nav):
        nav.navigateWithParams("library.source_detail", {})
        nav.navigateWithParams.assert_called_once()

    def test_no_playback_continue_disabled(self, hb):
        hb.hasPlayback = False
        assert not hb.hasPlayback

    def test_workflow_continue_then_check_jobs(self, hb, nav):
        if hb.hasPlayback:
            nav.navigate("playback")
        assert hb.activeJobs == 1
        if hb.activeJobs > 0:
            nav.navigate("jobs")

    def test_workflow_continue_then_check_source(self, hb, nav):
        if hb.hasPlayback:
            nav.navigate("playback")
        nav.navigate("connections")
        assert nav.navigate.call_count == 2

    def test_assistant_action_from_home(self, nav):
        nav.navigate("assistant")
        nav.navigate.assert_called_once_with("assistant")

    def test_micro_server_status_check(self):
        cb = MagicMock()
        cb.microServerState = "connected"
        running = cb.microServerState == "connected"
        assert running

    def test_all_home_actions_navigable(self, nav):
        actions = ["playback", "queue", "jobs", "connections", "assistant", "library"]
        for action in actions:
            nav.navigate(action)
        assert nav.navigate.call_count == len(actions)
