"""Tests for Radio v12 — sin operaciones sincronas prolongadas en UI thread."""
from unittest.mock import MagicMock

import pytest


class TestRadioBridgeCreation:
    def test_requires_player(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        with pytest.raises(Exception):
            RadioBridge()

    def test_creation(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        assert rb is not None

    def test_stations_default(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        assert len(rb.stations) == 0

    def test_favorites_default(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        assert len(rb.favorites) == 0

    def test_history_default(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        assert len(rb.history) == 0


class TestRadioOperations:
    def test_refresh(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        result = rb.refresh()
        assert isinstance(result, dict)

    def test_add_station(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.add.return_value = MagicMock(id=1)
        rb = RadioBridge(player_service=MagicMock(), radio_manager=mgr)
        result = rb.addStation("Test", "http://stream.url", "MP3", "US")
        assert result.get("ok")

    def test_add_station_empty_url(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        result = rb.addStation("Test", "", "MP3", "")
        assert not result.get("ok")

    def test_play_station(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        player = MagicMock()
        player.play_url = MagicMock()
        rb = RadioBridge(player_service=player)
        result = rb.playStation("http://stream.url", "Test Station")
        assert result.get("ok")

    def test_stop_stream(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        player = MagicMock()
        player.stop = MagicMock()
        rb = RadioBridge(player_service=player)
        result = rb.stopStream()
        assert result.get("ok")

    def test_cancel_stream(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        player = MagicMock()
        player.stop = MagicMock()
        rb = RadioBridge(player_service=player)
        result = rb.cancelStream()
        assert result.get("ok")

    def test_delete_station(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.remove_station.return_value = None
        rb = RadioBridge(player_service=MagicMock(), radio_manager=mgr)
        result = rb.deleteStation("http://stream.url")
        assert result.get("ok")

    def test_toggle_favorite(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.toggle_favorite.return_value = True
        rb = RadioBridge(player_service=MagicMock(), radio_manager=mgr)
        result = rb.toggleFavorite(1)
        assert isinstance(result, dict)

    def test_search(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.get_all.return_value = []
        rb = RadioBridge(player_service=MagicMock(), radio_manager=mgr)
        result = rb.search("rock")
        assert isinstance(result, dict)

    def test_export_m3u(self):
        import tempfile
        import os
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        rb._stations = [{"name": "Test", "url": "http://stream.url"}]
        with tempfile.NamedTemporaryFile(suffix=".m3u", delete=False) as f:
            result = rb.exportM3u(f.name)
            assert result.get("ok")
            os.unlink(f.name)

    def test_export_opml(self):
        import tempfile
        import os
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        rb._stations = [{"name": "Test", "url": "http://stream.url"}]
        with tempfile.NamedTemporaryFile(suffix=".opml", delete=False) as f:
            result = rb.exportOpml(f.name)
            assert result.get("ok")
            os.unlink(f.name)

    def test_get_metadata(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.get_metadata.return_value = {"ok": True}
        rb = RadioBridge(player_service=MagicMock(), radio_manager=mgr)
        result = rb.getMetadata("http://stream.url")
        assert isinstance(result, dict)

    def test_parse_playlist_file(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        stations = rb.parsePlaylistFile("#EXTM3U\n#EXTINF:-1,Test\nhttp://stream.url\n")
        assert len(stations) > 0

    def test_get_bitrate(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        rb = RadioBridge(player_service=MagicMock())
        assert rb.getBitrate() == 0
