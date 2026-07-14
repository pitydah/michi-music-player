"""Test DeviceDetailPage loads with mock device data, states, and bridge."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = False
    return mgr


class TestDeviceDetailLoad:
    def test_bridge_constructed_with_deps(self, mock_sync_mgr):
        """Bridge accepts dependencies by constructor — no service construction inside."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        assert bridge._sync_mgr is mock_sync_mgr

    def test_bridge_null_sync_manager_graceful(self):
        """Handle null bridge gracefully — no crash on start/stop."""
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.serverActive is False
        result = bridge.startServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_bridge_stop_without_start(self, mock_sync_mgr):
        """Stop without start returns ok."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.stopServer()
        assert result["ok"] is True

    def test_bridge_refresh_no_manager(self):
        """Refresh with null manager returns ok with zero counts."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.refresh()
        assert result["ok"] is True
        assert result["peers"] == 0
        assert result["paired"] == 0

    def test_bridge_load_device_detail_no_service(self):
        """loadDeviceDetail returns error with no sync manager."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.loadDeviceDetail("test_device")
        assert result["ok"] is False

    def test_bridge_load_device_detail_empty(self, mock_sync_mgr):
        """loadDeviceDetail with empty device key returns error."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.loadDeviceDetail("")
        assert result["ok"] is False

    def test_bridge_discover_no_service(self):
        """discoverDevices returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.discoverDevices()
        assert result["ok"] is False
        assert result["error"] == "NO_DEVICE_SYNC_SERVICE"

    def test_bridge_discover_with_mock(self, mock_sync_mgr):
        """discoverDevices with mock service returns error (no dev_svc)."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.discoverDevices()
        assert result["ok"] is False

    def test_bridge_discovered_initially_empty(self, mock_sync_mgr):
        """discovered list is empty initially."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        assert bridge.discovered == []

    def test_bridge_eject_no_service(self):
        """ejectDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.ejectDevice("/media/test")
        assert result["ok"] is False

    def test_bridge_eject_empty_path(self, mock_sync_mgr):
        """ejectDevice with empty path returns error."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.ejectDevice("")
        assert result["ok"] is False

    def test_device_storage_with_valid_mount(self, mock_sync_mgr, tmp_path):
        """deviceDetailStorage returns error without dev_svc."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        music = tmp_path / "Music"
        music.mkdir()
        result = bridge.deviceDetailStorage(str(music))
        assert result["ok"] is False

    def test_device_storage_no_service(self):
        """deviceDetailStorage returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.deviceDetailStorage("/media/test")
        assert result["ok"] is False

    def test_device_compatibility_no_service(self):
        """deviceDetailCompatibility returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.deviceDetailCompatibility("/media/test")
        assert result["ok"] is False

    def test_validate_audio_no_service(self):
        """validateAudioFile works without service (extension-based)."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.validateAudioFile("/music/track.flac")
        assert result["ok"] is True

    def test_validate_audio_video_not_supported(self, mock_sync_mgr, tmp_path):
        """validateAudioFile rejects video formats even without dev_svc."""
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        path = str(tmp_path / "video.mp4")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_pair_device_no_service(self):
        """pairDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.pairDevice("/media/test")
        assert result["ok"] is False

    def test_unpair_device_no_service(self):
        """unpairDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.unpairDevice("test_key")
        assert result["ok"] is False

    def test_trust_device_no_service(self):
        """trustDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.trustDevice("test_key")
        assert result["ok"] is False

    def test_untrust_device_no_service(self):
        """untrustDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.untrustDevice("test_key")
        assert result["ok"] is False

    def test_authorize_device_no_service(self):
        """authorizeDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.authorizeDevice("test_key")
        assert result["ok"] is False

    def test_unauthorize_device_no_service(self):
        """unauthorizeDevice returns error with no service."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.unauthorizeDevice("test_key")
        assert result["ok"] is False
