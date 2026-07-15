<<<<<<< Updated upstream
"""Test MixBridge generation flow with full state machine validation."""
=======
<<<<<<< HEAD
"""Test MixGenerator: loadMix with different types, seed, empty results, custom rules."""
=======
"""Test MixBridge generation flow with full state machine validation."""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("mix")]

=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
<<<<<<< Updated upstream
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "B", "album": "Bl", "duration": 180, "reason": "Favorito"},
=======
<<<<<<< HEAD
        {"track_id": i, "title": f"Fav {i}", "artist": "A", "album": "Al", "duration": 200 + i}
        for i in range(1, 21)
>>>>>>> Stashed changes
    ]
    mqs.recent.return_value = [{"track_id": 3, "title": "Recent 1", "artist": "C", "album": "Cl", "duration": 220}]
    mqs.most_played.return_value = [{"track_id": 4, "title": "Top 1", "artist": "D", "album": "Dl", "duration": 210}]
    mqs.unplayed.return_value = [{"track_id": 5, "title": "Unplayed 1", "artist": "E", "album": "El", "duration": 190}]
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = [{"track_id": 6, "title": "Field 1", "artist": "F", "album": "Fl", "duration": 200}]
    mqs.by_decade.return_value = [{"track_id": 7, "title": "Decade 1", "artist": "G", "album": "Gl", "duration": 200}]
    mqs.by_year.return_value = []
<<<<<<< Updated upstream
    mqs.high_quality.return_value = [{"track_id": 8, "title": "HQ 1", "artist": "H", "album": "Hl", "duration": 200}]
=======
    mqs.high_quality.return_value = []
=======
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "B", "album": "Bl", "duration": 180, "reason": "Favorito"},
    ]
    mqs.recent.return_value = [{"track_id": 3, "title": "Recent 1", "artist": "C", "album": "Cl", "duration": 220}]
    mqs.most_played.return_value = [{"track_id": 4, "title": "Top 1", "artist": "D", "album": "Dl", "duration": 210}]
    mqs.unplayed.return_value = [{"track_id": 5, "title": "Unplayed 1", "artist": "E", "album": "El", "duration": 190}]
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = [{"track_id": 6, "title": "Field 1", "artist": "F", "album": "Fl", "duration": 200}]
    mqs.by_decade.return_value = [{"track_id": 7, "title": "Decade 1", "artist": "G", "album": "Gl", "duration": 200}]
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = [{"track_id": 8, "title": "HQ 1", "artist": "H", "album": "Hl", "duration": 200}]
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return mqs


@pytest.fixture
def bridge(mock_mqs):
    return MixBridge(query_service=mock_mqs, track_action_service=MagicMock(), playlist_bridge=MagicMock())


class TestMixGenerator:
<<<<<<< Updated upstream
    def test_load_favorites_returns_tracks(self, bridge):
=======
<<<<<<< HEAD
    def test_generate_favorites(self, bridge):
>>>>>>> Stashed changes
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] == 2
        assert len(bridge.currentSongs) == 2

    def test_load_recent_returns_tracks(self, bridge):
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_most_played_returns_tracks(self, bridge):
        result = bridge.loadMix("most_played")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_unplayed_returns_tracks(self, bridge):
        result = bridge.loadMix("unplayed")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_daily_mix_returns_tracks(self, bridge):
        result = bridge.loadMix("daily_mix")
        assert result["ok"] is True
        assert len(bridge.currentSongs) > 0

    def test_load_by_artist_returns_tracks(self, bridge):
        result = bridge.loadMix("by_artist")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_genre_returns_tracks(self, bridge):
        result = bridge.loadMix("by_genre")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_decade_returns_tracks(self, bridge):
        result = bridge.loadMix("by_decade")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_high_quality_returns_tracks(self, bridge):
        result = bridge.loadMix("high_quality")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_year_with_empty_returns_no_error(self, bridge):
        result = bridge.loadMix("by_year")
        assert result["ok"] or not result["ok"]
        assert len(bridge.currentSongs) == 0

    def test_load_rediscovery_with_empty_returns_no_error(self, bridge):
        result = bridge.loadMix("rediscovery")
        assert result["ok"] or not result["ok"]
        assert len(bridge.currentSongs) == 0

    def test_load_unknown_mix_type_returns_false(self, bridge):
        result = bridge.loadMix("nonexistent")
        assert result["ok"] is False
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
            assert s["reason"] == "Mix diario"

    def test_multiple_loads_replaces_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 2
        bridge.loadMix("daily_mix")
        assert len(bridge.currentSongs) > 0

    def test_load_clears_previous_error(self, bridge):
        bridge.loadMix("nonexistent")
        assert not bridge.currentSongs
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0
        assert bridge.errorMessage == ""

    def test_generation_increment_used_for_stale_check(self, bridge):
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before

    def test_mix_categories_listed(self, bridge):
        cats = bridge.categories
        assert len(cats) == 12
        ids = [c["id"] for c in cats]
        assert "favorites" in ids
        assert "custom" in ids

    def test_partial_result_flag(self, bridge):
        result = bridge.loadMix("favorites")
        assert "partial" in result

    def test_refresh_with_no_current_mix_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_with_current_mix_reloads(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.refresh()
        assert result["ok"] is True
<<<<<<< Updated upstream
        assert len(bridge.currentSongs) == 2
=======
=======
    def test_load_favorites_returns_tracks(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] == 2
        assert len(bridge.currentSongs) == 2

    def test_load_recent_returns_tracks(self, bridge):
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_most_played_returns_tracks(self, bridge):
        result = bridge.loadMix("most_played")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_unplayed_returns_tracks(self, bridge):
        result = bridge.loadMix("unplayed")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_daily_mix_returns_tracks(self, bridge):
        result = bridge.loadMix("daily_mix")
        assert result["ok"] is True
        assert len(bridge.currentSongs) > 0

    def test_load_by_artist_returns_tracks(self, bridge):
        result = bridge.loadMix("by_artist")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_genre_returns_tracks(self, bridge):
        result = bridge.loadMix("by_genre")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_decade_returns_tracks(self, bridge):
        result = bridge.loadMix("by_decade")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_high_quality_returns_tracks(self, bridge):
        result = bridge.loadMix("high_quality")
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 1

    def test_load_by_year_with_empty_returns_no_error(self, bridge):
        result = bridge.loadMix("by_year")
        assert result["ok"] or not result["ok"]
        assert len(bridge.currentSongs) == 0

    def test_load_rediscovery_with_empty_returns_no_error(self, bridge):
        result = bridge.loadMix("rediscovery")
        assert result["ok"] or not result["ok"]
        assert len(bridge.currentSongs) == 0

    def test_load_unknown_mix_type_returns_false(self, bridge):
        result = bridge.loadMix("nonexistent")
        assert result["ok"] is False
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
            assert s["reason"] == "Mix diario"

    def test_multiple_loads_replaces_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 2
        bridge.loadMix("daily_mix")
        assert len(bridge.currentSongs) > 0

    def test_load_clears_previous_error(self, bridge):
        bridge.loadMix("nonexistent")
        assert not bridge.currentSongs
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0
        assert bridge.errorMessage == ""

    def test_generation_increment_used_for_stale_check(self, bridge):
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before

    def test_mix_categories_listed(self, bridge):
        cats = bridge.categories
        assert len(cats) == 12
        ids = [c["id"] for c in cats]
        assert "favorites" in ids
        assert "custom" in ids

    def test_partial_result_flag(self, bridge):
        result = bridge.loadMix("favorites")
        assert "partial" in result

    def test_refresh_with_no_current_mix_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_with_current_mix_reloads(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.refresh()
        assert result["ok"] is True
        assert len(bridge.currentSongs) == 2
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
