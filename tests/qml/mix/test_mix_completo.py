from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge, MixState


@pytest.fixture
def mock_mix_svc():
    svc = MagicMock()
    svc.favorites.return_value = [
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "B", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "A", "album": "B", "duration": 180, "reason": "Favorito"},
    ]
    svc.recent.return_value = [
        {"track_id": 3, "title": "Recent 1", "artist": "C", "album": "D", "duration": 220},
    ]
    svc.most_played.return_value = [
        {"track_id": 4, "title": "Top 1", "artist": "D", "album": "E", "duration": 210},
    ]
    svc.unplayed.return_value = [
        {"track_id": 5, "title": "Unplayed 1", "artist": "E", "album": "F", "duration": 190},
    ]
    svc.rediscovery.return_value = []
    svc.by_field.return_value = [
        {"track_id": 6, "title": "Field 1", "artist": "F", "album": "G", "duration": 200},
    ]
    svc.by_decade.return_value = [
        {"track_id": 7, "title": "Decade 1", "artist": "G", "album": "H", "duration": 200},
    ]
    svc.by_year.return_value = []
    svc.high_quality.return_value = [
        {"track_id": 8, "title": "HQ 1", "artist": "H", "album": "I", "duration": 200},
    ]
    return svc


@pytest.fixture
def mock_services():
    return {
        "playback_svc": MagicMock(),
        "queue_svc": MagicMock(),
        "playlist_svc": MagicMock(),
        "nav": MagicMock(),
        "page_state": MagicMock(),
        "job_svc": MagicMock(),
    }


@pytest.fixture
def bridge(mock_mix_svc, mock_services):
    return MixBridge(
        mix_service=mock_mix_svc,
        playback_service=mock_services["playback_svc"],
        queue_service=mock_services["queue_svc"],
        playlist_service=mock_services["playlist_svc"],
        navigation_bridge=mock_services["nav"],
        page_state_store=mock_services["page_state"],
        job_service=mock_services["job_svc"],
    )


class TestMixCompleto:

    def test_initial_state_idle(self, bridge):
        assert bridge.state == MixState.IDLE
        assert bridge.stateName == "IDLE"

    def test_configure_valid_category(self, bridge):
        result = bridge.configure("favorites")
        assert result.get("ok") is True
        assert bridge.state == MixState.CONFIGURING
        assert bridge.currentMixId == "favorites"
        assert bridge.currentMixTitle == "Favoritos"

    def test_configure_unknown_category(self, bridge):
        result = bridge.configure("nonexistent")
        assert result.get("ok") is False
        assert bridge.state == MixState.FAILED

    def test_validate_after_configure(self, bridge):
        bridge.configure("favorites")
        result = bridge.validate()
        assert result.get("ok") is True
        assert result.get("valid") is True

    def test_validate_without_configure_fails(self, bridge):
        result = bridge.validate()
        assert result.get("ok") is False

    def test_configure_validate_generate_full_flow(self, bridge):
        result = bridge.loadMix("favorites")
        assert result.get("ok") is True
        assert result.get("count") == 2
        assert bridge.state == MixState.READY
        assert len(bridge.currentSongs) == 2

    def test_generate_empty_result(self, bridge):
        bridge._mix_svc.favorites.return_value = []
        result = bridge.loadMix("favorites")
        assert result.get("ok") is True
        assert result.get("count") == 0
        assert bridge.state == MixState.READY

    def test_generate_service_none(self):
        b = MixBridge()
        result = b.loadMix("favorites")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_regenerate_from_ready(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.regenerate()
        assert result.get("ok") is True

    def test_cancel_generation(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.cancelGeneration()
        assert result.get("ok") is True
        assert bridge.state == MixState.CANCELLED

    def test_cancel_sets_cancelled_state(self, bridge):
        bridge.configure("favorites")
        bridge._set_state(MixState.GENERATING)
        result = bridge.cancelGeneration()
        assert result.get("ok") is True
        assert bridge.state == MixState.CANCELLED

    def test_reset_to_idle(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.reset()
        assert result.get("ok") is True
        assert bridge.state == MixState.IDLE
        assert bridge.currentMixId == ""

    def test_play_mix_success(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playMix()
        assert result.get("ok") is True

    def test_play_empty_mix_returns_error(self, bridge):
        result = bridge.playMix()
        assert result.get("ok") is False
        assert result.get("error_code") == "EMPTY_MIX"

    def test_enqueue_mix_success(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueMix()
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_enqueue_empty_mix_returns_error(self, bridge):
        result = bridge.enqueueMix()
        assert result.get("ok") is False
        assert result.get("error_code") == "EMPTY_MIX"

    def test_save_mix_as_playlist(self, bridge):
        bridge._playlist_svc.create.return_value = 42
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("My Mix")
        assert result.get("ok") is True
        assert result.get("count") == 2

    def test_save_mix_empty_name(self, bridge):
        result = bridge.saveMixAsPlaylist("")
        assert result.get("ok") is False
        assert result.get("error_code") == "EMPTY_NAME"

    def test_save_mix_no_playlist_service(self):
        b = MixBridge(mix_service=MagicMock())
        b._current_songs = [{"track_id": 1, "title": "Test"}]
        result = b.saveMixAsPlaylist("test")
        assert result.get("ok") is False
        assert result.get("error_code") == "NO_PLAYLIST_SERVICE"

    def test_play_from_index_valid(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result.get("ok") is True

    def test_play_from_index_invalid(self, bridge):
        result = bridge.playFromIndex(999)
        assert result.get("ok") is False
        assert result.get("error_code") == "INVALID_INDEX"

    def test_enqueue_track_valid(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueTrack(0)
        assert result.get("ok") is True

    def test_enqueue_track_invalid(self, bridge):
        result = bridge.enqueueTrack(999)
        assert result.get("ok") is False
        assert result.get("error_code") == "INVALID_INDEX"

    def test_explain_populated_mix(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.explainCurrentMix()
        assert result.get("ok") is True
        assert result.get("total") == 2

    def test_explain_empty_mix(self, bridge):
        result = bridge.explainCurrentMix()
        assert result.get("ok") is False
        assert result.get("error_code") == "EMPTY_MIX"

    def test_partial_failure_report_no_failures(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.partialFailureReport()
        assert result.get("has_failures") is False

    def test_categories_listed(self, bridge):
        cats = bridge.categories
        assert len(cats) == 12
        ids = [c["id"] for c in cats]
        assert "favorites" in ids
        assert "custom" in ids

    def test_state_machine_transitions(self, bridge):
        assert bridge._can_transition(MixState.CONFIGURING) is True
        bridge._set_state(MixState.CONFIGURING)
        assert bridge._can_transition(MixState.VALIDATING) is True
        assert bridge._can_transition(MixState.GENERATING) is False
        bridge._set_state(MixState.VALIDATING)
        assert bridge._can_transition(MixState.QUEUED) is True

    def test_state_changed_signal(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda s: signals.append(s))
        bridge._set_state(MixState.CONFIGURING)
        assert "CONFIGURING" in signals

    def test_generate_state_progression(self, bridge):
        bridge.configure("favorites")
        assert bridge.state == MixState.CONFIGURING
        bridge.validate()
        assert bridge.state == MixState.QUEUED
        result = bridge.generate()
        assert result.get("ok") is True
        assert bridge.state == MixState.READY

    def test_state_persists_via_page_store(self, bridge, mock_services):
        bridge.loadMix("favorites")
        mock_services["page_state"].set.assert_called_once()

    def test_daily_mix_has_reasons(self, bridge):
        bridge.loadMix("daily_mix")
        for s in bridge.currentSongs:
            assert "reason" in s

    def test_custom_mix_with_artist_seed(self, bridge):
        bridge._mix_svc.by_field.return_value = [{"track_id": 9, "title": "Custom", "artist": "Genesis"}]
        result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 5}')
        assert result.get("ok") is True

    def test_custom_mix_with_genre_seed(self, bridge):
        bridge._mix_svc.by_field.return_value = [{"track_id": 10, "title": "Custom", "artist": "Rock"}]
        result = bridge.loadMix("custom", seed='{"genre": "Rock", "limit": 10}')
        assert result.get("ok") is True

    def test_deduplication(self, bridge):
        bridge._mix_svc.favorites.return_value = [
            {"track_id": 1, "title": "A", "artist": "X"},
            {"track_id": 1, "title": "A dup", "artist": "X"},
        ]
        result = bridge.loadMix("favorites")
        assert result.get("count") == 1

    def test_no_false_empty_list_success(self, bridge):
        bridge._mix_svc = None
        result = bridge.loadMix("favorites")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"
