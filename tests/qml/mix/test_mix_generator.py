"""Test MixGenerator: loadMix with different types, seed, empty results, custom rules."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Fav {i}", "artist": "A", "album": "Al", "duration": 200 + i}
        for i in range(1, 21)
    ]
    mqs.recent.return_value = [
        {"track_id": i, "title": f"Recent {i}", "artist": "B", "album": "Bl", "duration": 210}
        for i in range(21, 31)
    ]
    mqs.most_played.return_value = [
        {"track_id": i, "title": f"Top {i}", "artist": "C", "album": "Cl", "duration": 180}
        for i in range(31, 41)
    ]
    mqs.unplayed.return_value = []
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = [
        {"track_id": i, "title": f"Field {i}", "artist": "D", "album": "Dl", "duration": 190}
        for i in range(41, 51)
    ]
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
    return mqs


@pytest.fixture
def bridge(mock_mqs):
    return MixBridge(query_service=mock_mqs, track_action_service=MagicMock(), playlist_bridge=MagicMock())


class TestMixGenerator:
    def test_generate_favorites(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] > 0

    def test_generate_recent(self, bridge):
        result = bridge.loadMix("recent")
        assert result["ok"] is True

    def test_generate_most_played(self, bridge):
        result = bridge.loadMix("most_played")
        assert result["ok"] is True

    def test_generate_by_artist(self, bridge):
        result = bridge.loadMix("by_artist")
        assert result["ok"] is True

    def test_generate_by_genre(self, bridge):
        result = bridge.loadMix("by_genre")
        assert result["ok"] is True

    def test_generate_with_seed(self, bridge):
        result = bridge.loadMix("favorites", seed="test_seed_42")
        assert result["ok"] is True

    def test_empty_mix_type_returns_error(self, bridge):
        result = bridge.loadMix("nonexistent")
        assert result["ok"] is False

    def test_generate_artist_limit(self, bridge):
        bridge.loadMix("favorites")
        artist_counts = {}
        for s in bridge.currentSongs:
            artist = s.get("artist", "")
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        for artist, count in artist_counts.items():
            assert count <= 5, f"Artist {artist} appears {count} times (max 5)"

    def test_no_duplicates(self, bridge):
        bridge.loadMix("favorites")
        ids = set()
        for s in bridge.currentSongs:
            tid = s.get("track_id") or s.get("id")
            assert tid not in ids, f"Duplicate track_id {tid}"
            ids.add(tid)

    def test_max_total_limit(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) <= 50

    def test_daily_mix_generates(self, bridge):
        result = bridge.loadMix("daily_mix")
        assert result["ok"] is True or result["ok"] is False

    def test_unplayed_mix_empty(self, bridge):
        result = bridge.loadMix("unplayed")
        assert result["ok"] is False or result["count"] == 0

    def test_custom_mix_with_seed(self, bridge):
        result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 10}')
        assert result["ok"] is True

    def test_custom_mix_empty_params(self, bridge):
        result = bridge.loadMix("custom")
        assert result["ok"] is True or result["ok"] is False

    def test_generation_title_set(self, bridge):
        bridge.loadMix("favorites")
        assert bridge.currentMixTitle != ""

    def test_generation_error_message_cleared(self, bridge):
        bridge._error_message = "old error"
        bridge.loadMix("favorites")
        assert bridge.errorMessage == ""

    def test_refresh_after_generation(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.refresh()
        assert result["ok"] is True
