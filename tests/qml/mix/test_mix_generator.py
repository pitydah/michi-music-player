"""Mix generator bridge tests against the durable-job contract.

Generation runs via the mix_generate job; the bridge exposes the canonical
outcome state 1:1 (COMPLETED_WITH_TRACKS / NO_MATCHES / ...) and an empty
result is NEVER ok.
"""
import pytest


from .conftest import default_tracks, make_bridge, make_mix_service


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=2)


@pytest.fixture
def bridge(mock_mqs, tmp_path):
    b, _svc = make_bridge(mock_mqs, tmp_path)
    return b


class TestMixGenerator:

    def test_load_favorites_returns_tracks(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert bridge.stateName == "COMPLETED_WITH_TRACKS"
        assert len(bridge.currentSongs) == 2

    def test_load_recent_returns_tracks(self, bridge):
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_most_played_returns_tracks(self, bridge):
        result = bridge.loadMix("most_played")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_unplayed_returns_tracks(self, bridge):
        result = bridge.loadMix("unplayed")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_daily_mix_returns_tracks(self, bridge):
        result = bridge.loadMix("daily_mix")
        assert result["ok"] is True
        assert len(bridge.currentSongs) > 0

    def test_load_by_artist_returns_tracks(self, bridge):
        result = bridge.loadMix("by_artist")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_by_genre_returns_tracks(self, bridge):
        result = bridge.loadMix("by_genre")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_by_decade_returns_tracks(self, bridge):
        result = bridge.loadMix("by_decade")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_high_quality_returns_tracks(self, bridge):
        result = bridge.loadMix("high_quality")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2

    def test_load_by_year_with_empty_is_no_matches(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": False, "status": "NO_MATCHES", "message": "Sin coincidencias",
            "strategy": strategy, "mix_id": f"query:{strategy}", "tracks": [],
        }
        result = bridge.loadMix("by_year")
        assert result["ok"] is True  # the job was accepted
        assert bridge.stateName == "NO_MATCHES"
        assert len(bridge.currentSongs) == 0

    def test_load_rediscovery_with_empty_is_no_matches(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": False, "status": "NO_MATCHES", "message": "Sin coincidencias",
            "strategy": strategy, "mix_id": f"query:{strategy}", "tracks": [],
        }
        result = bridge.loadMix("rediscovery")
        assert result["ok"] is True  # the job was accepted
        assert bridge.stateName == "NO_MATCHES"
        assert len(bridge.currentSongs) == 0

    def test_load_unknown_mix_type_returns_error(self, bridge):
        result = bridge.loadMix("nonexistent")
        assert result["ok"] is False
        assert result.get("error_code") == "UNKNOWN_CATEGORY"
        assert len(bridge.currentSongs) == 0

    def test_custom_mix_with_seed_artist(self, bridge):
        result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 5}')
        assert result["ok"] is True

    def test_custom_mix_with_seed_genre(self, bridge):
        result = bridge.loadMix("custom", seed='{"genre": "Rock", "limit": 10}')
        assert result["ok"] is True

    def test_generation_sets_current_mix_title(self, bridge):
        bridge.loadMix("favorites")
        assert bridge.currentMixTitle == "Favoritos"

    def test_generation_sets_current_mix_id(self, bridge):
        bridge.loadMix("favorites")
        assert bridge.currentMixId == "favorites"

    def test_daily_mix_has_reason_field(self, bridge):
        bridge.loadMix("daily_mix")
        for s in bridge.currentSongs:
            assert "reason" in s
            assert s["reason"]

    def test_multiple_loads_replaces_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 2
        bridge.loadMix("daily_mix")
        assert len(bridge.currentSongs) > 0

    def test_load_clears_previous_error(self, bridge):
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": False, "status": "NO_MATCHES", "message": "Sin coincidencias",
            "strategy": strategy, "mix_id": f"query:{strategy}", "tracks": [],
        }
        bridge.loadMix("by_year")
        bridge._mix_svc.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
            "ok": True, "status": "COMPLETED_WITH_TRACKS", "message": "Mix generado",
            "strategy": strategy, "mix_id": f"query:{strategy}",
            "tracks": default_tracks(strategy, 2), "count": 2,
        }
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0
        assert bridge.errorMessage == ""

    def test_generation_increment_used_for_stale_check(self, bridge):
        bridge.loadMix("favorites")
        assert bridge._generation >= 1

    def test_mix_categories_listed(self, bridge):
        cats = bridge.categories
        assert len(cats) == 12
        ids = [c["id"] for c in cats]
        assert "favorites" in ids
        assert "custom" in ids

    def test_generate_returns_job_shape(self, bridge):
        result = bridge.loadMix("favorites")
        assert "job_id" in result
        assert "state" in result

    def test_refresh_with_no_current_mix_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is False

    def test_refresh_with_current_mix_reloads(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.refresh()
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2
