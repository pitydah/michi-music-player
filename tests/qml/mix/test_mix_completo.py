from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge, MixState

from .conftest import make_bridge, make_mix_service


@pytest.fixture
def mock_mix_svc():
    return make_mix_service(default_track_count=2)


@pytest.fixture
def mock_services():
    queue_svc = MagicMock()
    queue_svc.replace_and_play.return_value = {"ok": True}
    queue_svc.enqueue.return_value = {"ok": True, "count": 2}
    return {
        "playback_svc": MagicMock(),
        "queue_svc": queue_svc,
        "playlist_svc": MagicMock(),
        "nav": MagicMock(),
        "page_state": MagicMock(),
        "job_svc": MagicMock(),
    }


@pytest.fixture
def bridge(mock_mix_svc, mock_services, tmp_path):
    b, _svc = make_bridge(
        mock_mix_svc, tmp_path,
        playback_service=mock_services["playback_svc"],
        queue_service=mock_services["queue_svc"],
        playlist_service=mock_services["playlist_svc"],
        navigation_bridge=mock_services["nav"],
        page_state_store=mock_services["page_state"],
    )
    return b


class TestMixCompleto:

    def test_initial_state_idle(self, bridge):
        assert bridge.state == MixState.IDLE
        assert bridge.stateName == "IDLE"

    def test_configure_valid_category(self, bridge):
        result = bridge.configure("favorites")
        assert result.get("ok") is True
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
        assert "job_id" in result
        assert bridge.state == MixState.COMPLETED_WITH_TRACKS
        assert len(bridge.currentSongs) == 2

    def test_generate_empty_result_is_not_success(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": False, "status": "NO_MATCHES", "message": "Sin coincidencias",
            "strategy": strategy, "mix_id": f"query:{strategy}", "tracks": [],
        }
        result = bridge.loadMix("favorites")
        assert result.get("ok") is True  # the job was accepted
        assert bridge.state == MixState.NO_MATCHES
        assert len(bridge.currentSongs) == 0
        assert bridge.errorMessage  # honest message, never silent success

    def test_generate_service_none(self):
        b = MixBridge()
        result = b.loadMix("favorites")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_regenerate_from_ready(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.regenerate()
        assert result.get("ok") is True
        assert len(bridge.currentSongs) > 0

    def test_cancel_generation(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.cancelGeneration()
        assert result.get("ok") is True
        assert bridge.state == MixState.CANCELLED

    def test_cancel_clears_songs(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == 0

    def test_reset_to_idle(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.reset()
        assert result.get("ok") is True
        assert bridge.state == MixState.IDLE
        assert bridge.currentMixId == ""

    def test_play_mix_success(self, bridge, mock_services):
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
        bridge._mix_svc.save_mix_as_playlist.return_value = {
            "ok": True, "status": "COMPLETED", "playlist_id": 42,
            "requested": 2, "added": 2, "failed": 0, "count": 2,
        }
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("My Mix")
        assert result.get("ok") is True
        assert result.get("count") == 2
        assert result.get("playlist_id") == 42

    def test_save_mix_empty_name(self, bridge):
        result = bridge.saveMixAsPlaylist("")
        assert result.get("ok") is False
        assert result.get("error_code") == "EMPTY_NAME"

    def test_save_mix_no_playlist_service(self):
        b = MixBridge(mix_service=None)
        b._current_songs = [{"track_id": 1, "title": "Test"}]
        result = b.saveMixAsPlaylist("test")
        assert result.get("ok") is False
        assert result.get("error_code") == "NO_PLAYLIST_SERVICE"

    def test_save_mix_direct_path_uses_real_id_never_dict(self):
        """Fallback path (no MixService): create()["id"] is the real id."""
        playlist_svc = MagicMock()
        playlist_svc.create.return_value = {"ok": True, "id": 42}
        playlist_svc.add_track.return_value = {"ok": True}
        b = MixBridge(mix_service=None, playlist_service=playlist_svc)
        b._current_songs = [{"track_id": 1, "title": "A"},
                            {"track_id": 2, "title": "B"}]
        result = b.saveMixAsPlaylist("Direct")
        assert result.get("ok") is True
        assert result.get("playlist_id") == 42
        assert not isinstance(result.get("playlist_id"), dict)
        calls = playlist_svc.add_track.call_args_list
        assert all(args[0][0] == 42 for args in calls), (
            "add_track must receive the real playlist id, never a dict")

    def test_save_mix_direct_path_never_full_success_when_empty(self):
        playlist_svc = MagicMock()
        playlist_svc.create.return_value = {"ok": True, "id": 7}
        playlist_svc.add_track.return_value = {"ok": False,
                                               "error": "ADD_TRACK_FAILED"}
        b = MixBridge(mix_service=None, playlist_service=playlist_svc)
        b._current_songs = [{"track_id": 1, "title": "A"}]
        result = b.saveMixAsPlaylist("Vacio")
        assert result.get("ok") is False
        assert result.get("added") == 0

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

    def test_state_changed_signal(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda s: signals.append(s))
        bridge._set_state(MixState.RUNNING)
        assert "RUNNING" in signals

    def test_generate_state_progression(self, bridge):
        bridge.configure("favorites")
        bridge.validate()
        result = bridge.generate()
        assert result.get("ok") is True
        assert bridge.state == MixState.COMPLETED_WITH_TRACKS

    def test_state_persists_via_page_store(self, bridge, mock_services):
        bridge.loadMix("favorites")
        mock_services["page_state"].set.assert_called_once()

    def test_daily_mix_has_reasons(self, bridge):
        bridge.loadMix("daily_mix")
        for s in bridge.currentSongs:
            assert "reason" in s

    def test_custom_mix_with_artist_seed(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": True, "status": "COMPLETED_WITH_TRACKS", "message": "Mix generado",
            "strategy": strategy, "mix_id": f"query:{strategy}",
            "tracks": [{"track_id": 9, "id": 9, "title": "Custom",
                        "artist": "Genesis", "reason": "Mix personalizado"}],
            "count": 1,
        }
        result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 5}')
        assert result.get("ok") is True
        assert len(bridge.currentSongs) == 1

    def test_custom_mix_with_genre_seed(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": True, "status": "COMPLETED_WITH_TRACKS", "message": "Mix generado",
            "strategy": strategy, "mix_id": f"query:{strategy}",
            "tracks": [{"track_id": 10, "id": 10, "title": "Custom",
                        "artist": "Rock", "reason": "Mix personalizado"}],
            "count": 1,
        }
        result = bridge.loadMix("custom", seed='{"genre": "Rock", "limit": 10}')
        assert result.get("ok") is True

    def test_generation_counter_used_for_stale_result(self, bridge):
        bridge.loadMix("favorites")
        bridge._generation += 1
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0

    def test_no_false_empty_list_success(self, bridge):
        bridge._mix_svc = None
        result = bridge.loadMix("favorites")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"
