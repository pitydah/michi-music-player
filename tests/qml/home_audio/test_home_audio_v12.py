"""Tests for Home Audio v12 — contractual functions completas."""
from unittest.mock import MagicMock



class TestHomeAudioBridgeCreation:
    def test_creation(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert hab is not None

    def test_initial_states(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert hab.homeAssistantState == "not_configured"
        assert hab.snapcastState == "unavailable"

    def test_receivers_available(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert isinstance(hab.receiversAvailable, bool)

    def test_zones_supported(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert isinstance(hab.zonesSupported, bool)

    def test_volume_supported(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert isinstance(hab.volumeSupported, bool)

    def test_offline_default(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert isinstance(hab.offline, bool)

    def test_latency_ms_default(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert isinstance(hab.latencyMs, int)

    def test_last_contact_default(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        assert hab.lastContact == 0.0


class TestHomeAudioOperations:
    def test_refresh(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge(ha_controller=MagicMock(), snapcast_ctrl=MagicMock())
        result = hab.refresh()
        assert result.get("ok")

    def test_disconnect(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge(ha_controller=MagicMock())
        result = hab.disconnectHa()
        assert result.get("ok")

    def test_set_zone_volume_no_snapcast(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.setZoneVolume("zone1", 0.5)
        assert not result.get("ok")

    def test_open_diagnostics(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.openDiagnostics()
        assert result.get("ok")
        assert "ha_state" in result

    def test_discover_receivers(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.discoverReceivers()
        assert isinstance(result, dict)

    def test_server_handoff(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.serverHandoff()
        assert not result.get("ok")

    def test_recover_from_offline(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.recoverFromOffline()
        assert result.get("ok")

    def test_get_latency_report(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.getLatencyReport()
        assert result.get("ok")

    def test_set_zone_mute(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        snap = MagicMock()
        snap.set_group_mute = MagicMock()
        hab = HomeAudioBridge(snapcast_ctrl=snap)
        result = hab.setZoneMute("zone1", True)
        assert result.get("ok")

    def test_reconnect_ha(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        ha = MagicMock()
        ha.test_connection.return_value = True
        hab = HomeAudioBridge(ha_controller=ha)
        result = hab.reconnectHa()
        assert isinstance(result, dict)

    def test_handoff_to_server(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        hab = HomeAudioBridge()
        result = hab.handoffToServer()
        assert not result.get("ok")
