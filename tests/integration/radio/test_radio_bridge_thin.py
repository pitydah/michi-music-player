"""RadioBridge thin-adapter integration (Slice 5, ADR-003).

The bridge must not keep parallel state and must route every operation to the
injected canonical service API.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from ui_qml_bridge.radio_bridge import RadioBridge


class TestBridgeThin:
    def test_bridge_has_no_history_attribute(self):
        bridge = RadioBridge(player_service=MagicMock())
        assert not hasattr(bridge, "_history")
        assert not hasattr(bridge, "_add_to_history")

    def test_refresh_reads_service(self):
        svc = MagicMock()
        svc.get_stations.return_value = [
            {"id": 1, "name": "Jazz FM", "url": "http://jazz.stream",
             "codec": "MP3", "country": "US", "tags": [], "favorite": True,
             "image_path": "", "bitrate": 128},
        ]
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        result = bridge.refresh()
        assert result["ok"] and result["count"] == 1
        assert bridge.stations[0]["name"] == "Jazz FM"
        svc.get_stations.assert_called_once()

    def test_crud_reaches_service(self):
        svc = MagicMock()
        svc.get_stations.return_value = [
            {"id": 7, "name": "Rock FM", "url": "http://rock.stream",
             "codec": "AAC", "country": "UK", "tags": [], "favorite": False,
             "image_path": "", "bitrate": 0},
        ]
        svc.add_station.return_value = {"ok": True, "id": 8}
        svc.edit_station.return_value = {"ok": True}
        svc.delete_station.return_value = {"ok": True}
        svc.favorite_station.return_value = {"ok": True, "favorite": True}
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        bridge.refresh()

        bridge.addStation("New", "http://new.stream", "MP3", "DE")
        svc.add_station.assert_called_once_with(
            "New", "http://new.stream", genre="", country="DE", codec="MP3")

        bridge.editStation(7, "Edited", "http://edited.stream", "AAC", "UK")
        svc.edit_station.assert_called_once_with(
            7, name="Edited", url="http://edited.stream", codec="AAC", country="UK")

        bridge.toggleFavorite(7)
        svc.favorite_station.assert_called_once_with(7)

        bridge.deleteStation("http://rock.stream")
        svc.delete_station.assert_called_once_with(7)

    def test_history_reads_service(self):
        svc = MagicMock()
        svc.get_history.return_value = [
            {"station_id": 1, "started_at": "2026-01-01T00:00:00",
             "station_name": "Jazz FM", "stream_url": "http://jazz.stream"},
        ]
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        history = bridge.history
        assert len(history) == 1
        assert history[0]["name"] == "Jazz FM"
        assert history[0]["url"] == "http://jazz.stream"
        svc.get_history.assert_called_once_with(50)

    def test_clear_history_delegates(self):
        svc = MagicMock()
        svc.clear_history.return_value = {"ok": True}
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        result = bridge.clearHistory()
        assert result["ok"] is True
        svc.clear_history.assert_called_once()

    def test_is_playing_confirmed_not_optimistic(self):
        svc = MagicMock()
        svc.play_station.return_value = {"ok": True, "accepted": True, "status": "buffering"}
        player = MagicMock()
        bridge = RadioBridge(radio_manager=svc, player_service=player)
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"] is True
        assert result["accepted"] is True
        svc.play_station.assert_called_once_with("http://jazz.stream", "Jazz FM")
        assert bridge.isPlaying is False  # not confirmed yet
        assert bridge.isBuffering is False  # no optimistic buffering either
        # Confirmation comes only from the service state event (readback).
        bridge._on_service_state_event(type("Evt", (), {"data": {"state": "playing"}})())
        assert bridge.isPlaying is True
        assert bridge.isBuffering is False

    def test_play_delegates_and_service_owns_history(self):
        svc = MagicMock()
        svc.get_stations.return_value = [
            {"id": 3, "name": "Jazz FM", "url": "http://jazz.stream",
             "codec": "MP3", "country": "US", "tags": [], "favorite": False,
             "image_path": "", "bitrate": 0},
        ]
        svc.play_station.return_value = {"ok": True, "accepted": True, "status": "buffering"}
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"] is True
        svc.play_station.assert_called_once_with("http://jazz.stream", "Jazz FM")
        # The bridge never records plays: the canonical service owns history.
        svc.mark_played.assert_not_called()
        bridge._on_service_state_event(type("Evt", (), {"data": {"state": "playing"}})())
        svc.mark_played.assert_not_called()

    def test_play_station_failure_is_explicit(self):
        svc = MagicMock()
        svc.play_station.return_value = {"ok": False, "error": "BACKEND_UNAVAILABLE"}
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"] is False
        assert result["error"] == "BACKEND_UNAVAILABLE"
        assert bridge.isPlaying is False

    def test_stop_stream_delegates(self):
        svc = MagicMock()
        svc.stop.return_value = {"ok": True}
        bridge = RadioBridge(radio_manager=svc, player_service=MagicMock())
        result = bridge.stopStream()
        assert result["ok"] is True
        svc.stop.assert_called_once()
