from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MixBridge

from .conftest import make_bridge, make_mix_service


@pytest.fixture
def empty_mqs():
    """Every strategy yields an honest NO_MATCHES (never an empty success)."""
    return make_mix_service(outcomes={
        s: {"ok": False, "status": "NO_MATCHES",
            "message": "Ninguna canción coincide con el criterio del mix",
            "strategy": s, "mix_id": f"query:{s}", "tracks": []}
        for s in ("favorites", "recent", "unplayed", "rediscovery",
                  "most_played", "by_field", "by_decade", "by_year",
                  "high_quality")
    })


@pytest.fixture
def failing_mqs():
    svc = MagicMock()
    svc.generate.side_effect = RuntimeError("DB fail")
    return svc


class TestMixNegative:
    def test_no_query_service_returns_no_songs(self):
        bridge = MixBridge()
        result = bridge.loadMix("favorites")
        assert result["ok"] is False
        assert result["error_code"] == "SERVICE_UNAVAILABLE"
        assert len(bridge.currentSongs) == 0

    def test_no_candidates_is_not_success(self, empty_mqs, tmp_path):
        bridge, _svc = make_bridge(empty_mqs, tmp_path)
        result = bridge.loadMix("favorites")
        assert result["ok"] is True  # the JOB was accepted
        assert bridge.stateName == "NO_MATCHES"
        assert len(bridge.currentSongs) == 0
        assert bridge.errorMessage  # honest message, not silent empty success

    def test_no_candidates_for_recent(self, empty_mqs, tmp_path):
        bridge, _svc = make_bridge(empty_mqs, tmp_path)
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert bridge.stateName == "NO_MATCHES"
        assert len(bridge.currentSongs) == 0

    def test_no_candidates_for_unplayed(self, empty_mqs, tmp_path):
        bridge, _svc = make_bridge(empty_mqs, tmp_path)
        result = bridge.loadMix("unplayed")
        assert result["ok"] is True
        assert bridge.stateName == "NO_MATCHES"

    def test_no_candidates_for_rediscovery(self, empty_mqs, tmp_path):
        bridge, _svc = make_bridge(empty_mqs, tmp_path)
        result = bridge.loadMix("rediscovery")
        assert result["ok"] is True
        assert bridge.stateName == "NO_MATCHES"

    def test_db_failure_fails_the_job(self, failing_mqs, tmp_path):
        bridge, job_svc = make_bridge(failing_mqs, tmp_path)
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 0
        assert bridge.stateName == "FAILED"
        jobs = job_svc.list_jobs(owner="mix")
        assert jobs[0]["state"] == "FAILED"

    def test_no_playback_service_play_mix(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test", "artist": "A"}]
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] in ("NO_PLAYBACK", "NO_TRACK_ID")

    def test_no_playlist_service_save_as_playlist(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test"}]
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] == "NO_PLAYLIST_SERVICE"

    def test_invalid_strategy_unknown_category(self, tmp_path):
        svc = make_mix_service()
        bridge, _svc = make_bridge(svc, tmp_path)
        result = bridge.loadMix("not_a_category")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_CATEGORY"
        assert len(bridge.currentSongs) == 0
