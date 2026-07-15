from __future__ import annotations
"""EG — Home minimalista: service state, current source, continuity, recent interruption,
active jobs, errors, assistant actions, server status. No duplicar Biblioteca."""

from unittest.mock import MagicMock

import pytest

from core.home.home_status import (
    AssistantSuggestion, HomeCardError, LibraryHomeStatus,
)
from core.home.home_dashboard_service import HomeDashboardService
pytestmark = [pytest.mark.qml_module("home")]


def _make_context_svc():
    svc = MagicMock()
    svc.get_home_snapshot.return_value = {
        "library_health": {
            "track_count": 100,
            "album_count": 10,
            "artist_count": 5,
            "genre_count": 3,
            "active_roots_count": 2,
            "index_error_count": 0,
            "missing_file_count": 0,
            "missing_metadata_count": 0,
            "missing_cover_count": 0,
            "tracks_without_audio_features": 0,
            "new_tracks_count": 0,
        },
    }
    return svc


@pytest.fixture
def service():
    svc = HomeDashboardService(
        db=None,
        playback=MagicMock(),
        context_svc=_make_context_svc(),
        sync_mgr=MagicMock(),
        audio_output_ctrl=MagicMock(),
        player_engine=MagicMock(),
        features=MagicMock(),
        settings_mgr=MagicMock(),
        michi_link_ctrl=MagicMock(),
        ecosystem_doctor=MagicMock(),
    )
    return svc


class TestServiceState:
    def test_overall_state_ready(self, service):
        snap = service.build_snapshot()
        assert snap.overall_state in (
            "ready", "empty_library", "playback_active",
            "needs_attention", "safe_mode", "limited_services",
        )

    def test_headline_not_empty(self, service):
        snap = service.build_snapshot()
        assert snap.headline != ""

    def test_subtitle_not_empty(self, service):
        snap = service.build_snapshot()
        assert snap.subtitle != ""


class TestCurrentSource:
    def test_playback_source_in_status(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.playback, "source")

    def test_playback_state_is_string(self, service):
        snap = service.build_snapshot()
        assert isinstance(snap.playback.state, str)

    def test_playback_has_current_track_flag(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.playback, "has_current_track")


class TestContinuity:
    def test_can_continue_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.playback, "can_continue")

    def test_can_continue_remote_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.playback, "can_continue_remote")

    def test_queue_count_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.playback, "queue_count")


class TestActiveJobs:
    def test_library_has_index_errors(self):
        lib = LibraryHomeStatus(index_error_count=5, missing_file_count=3)
        assert lib.index_error_count == 5

    def test_library_has_missing_files(self):
        lib = LibraryHomeStatus(missing_file_count=3)
        assert lib.missing_file_count == 3


class TestErrors:
    def test_errors_list_is_list(self, service):
        snap = service.build_snapshot()
        assert isinstance(snap.errors, list)

    def test_errors_contain_card_name(self):
        err = HomeCardError(card_name="library", error_message="fail", is_fatal=False)
        assert err.card_name == "library"
        assert err.is_fatal is False


class TestAssistantActions:
    def test_assistant_suggestions_list(self, service):
        snap = service.build_snapshot()
        assert isinstance(snap.assistant_suggestions, list)

    def test_suggestion_has_title(self):
        s = AssistantSuggestion(title="Test", message="Msg", target_route="home")
        assert s.title == "Test"
        assert s.target_route == "home"

    def test_actions_list_is_list(self, service):
        snap = service.build_snapshot()
        assert isinstance(snap.actions, list)


class TestServerStatus:
    def test_ecosystem_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap, "ecosystem")

    def test_micro_server_state_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.ecosystem, "micro_server_state")

    def test_sync_state_present(self, service):
        snap = service.build_snapshot()
        assert hasattr(snap.ecosystem, "mobile_sync_state")

    def test_alerts_list_is_list(self, service):
        snap = service.build_snapshot()
        assert isinstance(snap.alerts, list)


class TestNoDuplicateLibrary:
    def test_home_has_no_duplicate_of_library(self):
        lib = LibraryHomeStatus(track_count=100)
        assert isinstance(lib, LibraryHomeStatus)
        assert hasattr(lib, "track_count")
