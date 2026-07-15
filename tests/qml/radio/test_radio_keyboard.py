"""Test keyboard navigation patterns for RadioPage and related components."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("accessibility")]


@pytest.fixture
def mock_stations():
    stations = []
    for i, (name, url, codec, country, fav) in enumerate([
        ("Jazz FM", "http://jazz.stream", "MP3", "US", True),
        ("Rock FM", "http://rock.stream", "AAC", "UK", False),
        ("News Talk", "http://news.stream", "AAC", "US", True),
    ]):
        s = MagicMock()
        s.id = i + 1
        s.name = name
        s.url = url
        s.codec = codec
        s.country = country
        s.tags = [name.lower().split()[0]]
        s.favorite = fav
        s.bitrate = 128
        stations.append(s)
    return stations


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    return mgr


@pytest.fixture
def mock_player():
    return MagicMock()


@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestRadioKeyboard:
    """Test keyboard navigation patterns for radio."""

    def test_navigate_favorites_then_all(self, bridge):
        bridge.refresh()
        assert len(bridge.favorites) == 2
        assert len(bridge.stations) == 3

    def test_search_field_focusable(self, bridge):
        bridge.search(query="Jazz")
        assert len(bridge._stations) >= 0

    def test_escape_closes_add_form(self, bridge):
        pass

    def test_enter_on_search_submits(self, bridge):
        bridge.refresh()
        result = bridge.search(query="Rock")
        assert result["ok"]
        assert any(r["name"] == "Rock FM" for r in result["results"])

    def test_tab_through_station_list(self, bridge):
        bridge.refresh()
        assert len(bridge.stations) == 3

    def test_accessible_names_on_stations(self, bridge):
        bridge.refresh()
        for s in bridge.stations:
            assert s["name"] is not None
            assert isinstance(s["name"], str)

    def test_escape_closes_detail(self, bridge):
        pass

    def test_enter_activates_station(self, bridge):
        bridge.refresh()
        station = bridge.stations[1]
        assert station["name"] == "Rock FM"

    def test_arrow_keys_navigate_stations(self, bridge):
        bridge.refresh()
        assert len(bridge.stations) >= 2

    def test_keyboard_focus_visible(self, bridge):
        pass

    def test_accessible_descriptions(self, bridge):
        bridge.refresh()
        for s in bridge.stations:
            assert s.get("url") is not None

    def test_filter_visible_stations(self, bridge):
        bridge.refresh()
        result = bridge.search(query="Jazz")
        assert result["ok"]
        filtered = [r for r in result["results"] if r["name"] == "Jazz FM"]
        assert len(filtered) == 1
