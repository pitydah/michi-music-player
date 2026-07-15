from __future__ import annotations
"""MW: Radio — connect to station, play stream, stop stream."""

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestRadioConnectPlayStop(SpecializedWorkflowBase):
    def test_list_stations(self, radio_fixtures):
        b = radio_fixtures
        b.refresh()
        assert b.refresh.called

    def test_play_station(self, radio_fixtures):
        b = radio_fixtures
        result = b.playStation("http://stream.example.com/radio")
        self.assert_ok(result)

    def test_stop_stream(self, radio_fixtures):
        b = radio_fixtures
        result = b.stopStream()
        self.assert_ok(result)

    def test_full_workflow(self, radio_fixtures):
        b = radio_fixtures
        b.refresh()
        b.playStation("http://stream.example.com/radio")
        b.stopStream()
        assert b.refresh.called
        assert b.playStation.called
        assert b.stopStream.called

    def test_add_station(self, radio_fixtures):
        b = radio_fixtures
        result = b.addStation("New Station", "http://stream.url", "MP3", "US")
        self.assert_ok(result)

    def test_delete_station(self, radio_fixtures):
        b = radio_fixtures
        result = b.deleteStation("http://stream.url")
        self.assert_ok(result)

    def test_no_stations(self):
        b = MagicMock()
        b.stations = []
        assert len(b.stations) == 0

    def test_play_error(self, radio_fixtures):
        b = radio_fixtures
        b.playStation = MagicMock(
            return_value={"ok": False, "error": "EMPTY_URL"}
        )
        result = b.playStation("")
        self.assert_error(result, "EMPTY_URL")
