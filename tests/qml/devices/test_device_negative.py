<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test error states: missing service, empty device list, video rejection, etc."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test negative/edge cases: null bridge, empty states, errors."""
from __future__ import annotations

=======
"""Test error states: missing service, empty device list, video rejection, etc."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
<<<<<<< Updated upstream
from core.device_sync_service import (
    DeviceSyncService,
)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
from core.device_sync_service import DeviceSyncService, DeviceIdentity, DeviceProtocol
>>>>>>> Stashed changes
from ui_qml_bridge.devices_bridge import DevicesBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    (music / "video.avi").write_bytes(b"\x00" * 200)
    return tmp_path


@pytest.fixture
def dev_svc():
    return DeviceSyncService()


class TestDeviceNegative:
    """Test negative and error states."""

    def test_null_bridge_start_server(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_null_bridge_stop_server(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.stopServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_null_bridge_refresh(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.refresh()
        assert result["ok"] is True
        assert result["peers"] == 0
        assert result["paired"] == 0

    def test_null_bridge_load_device_detail(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.loadDeviceDetail("test_key")
        assert result["ok"] is False

    def test_null_bridge_discover_devices(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.discoverDevices()
        assert result["ok"] is False
        assert result["error"] == "NO_DEVICE_SYNC_SERVICE"

    def test_null_bridge_pair_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.pairDevice("/media/test")
        assert result["ok"] is False

    def test_null_bridge_unpair_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.unpairDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_trust_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.trustDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_authorize_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.authorizeDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_start_transfer(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/t.flac", "/dst/t.flac")
        assert result["ok"] is False

    def test_null_bridge_cancel_transfer(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.cancelTransfer("job_1")
        assert result["ok"] is False

    def test_null_bridge_validate_audio(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.validateAudioFile("/music/track.flac")
        assert result["ok"] is True

    def test_null_bridge_eject(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.ejectDevice("/media/test")
        assert result["ok"] is False

    def test_empty_paired_devices(self, dev_svc):
        assert dev_svc.get_paired() == []

    def test_empty_discovered_devices(self, dev_svc):
        assert dev_svc.get_discovered() == []

    def test_empty_transfer_jobs(self, dev_svc):
        assert dev_svc.list_jobs() == []

    def test_empty_history(self, dev_svc):
        assert dev_svc.get_history() == []

    def test_empty_errors(self, dev_svc):
        assert dev_svc.last_errors() == []

    def test_identify_nonexistent(self, dev_svc):
        assert dev_svc.identify("/nonexistent") is None

    def test_video_file_rejected_by_validation(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.mp4")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_avi_video_rejected_by_validation(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.avi")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_unknown_format_rejected(self, bridge, temp_music):
        path = str(temp_music / "unknown.xyz")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert "UNSUPPORTED_FORMAT" in result.get("error", "")

    def test_transfer_no_service_returns_error(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/t.flac", "/dst/t.flac")
        assert result["ok"] is False

    def test_cancel_nonexistent_transfer(self, bridge):
        result = bridge.cancelTransfer("nonexistent_job")
        assert result["ok"] is False

    def test_retry_nonexistent_transfer(self, bridge):
        result = bridge.retryTransfer("nonexistent_job")
        assert result["ok"] is False

    def test_server_active_false_without_start(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.serverActive is False

    def test_peers_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.peers == []

    def test_paired_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.pairedDevices == []

    def test_discovered_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.discovered == []

    def test_transfer_jobs_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.transferJobs == []

    def test_transfer_history_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.transferHistory == []

    def test_server_stop_before_start_returns_ok(self, mock_sync_mgr):
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.stopServer()
        assert result["ok"] is True

    def test_storage_info_none_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.storageInfo == []

    def test_compatibility_info_none_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.compatibilityInfo == []


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = False
    return mgr


<<<<<<< Updated upstream
@pytest.fixture
def bridge(mock_sync_mgr):
    return DevicesBridge(sync_manager=mock_sync_mgr)
=======
    def test_storage_info_initial(self):
        b = DevicesBridge()
        assert b.storageInfo == []

    def test_compat_info_initial(self):
        b = DevicesBridge()
        assert b.compatibilityInfo == []

    def test_bridge_has_state_property(self):
        b = DevicesBridge()
        assert hasattr(b, 'pageState')

    def test_bridge_has_error_message_property(self):
        b = DevicesBridge()
        assert hasattr(b, 'errorMessage')
=======
from core.device_sync_service import (
    DeviceSyncService,
)
from ui_qml_bridge.devices_bridge import DevicesBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    (music / "video.avi").write_bytes(b"\x00" * 200)
    return tmp_path


@pytest.fixture
def dev_svc():
    return DeviceSyncService()


class TestDeviceNegative:
    """Test negative and error states."""

    def test_null_bridge_start_server(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_null_bridge_stop_server(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.stopServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_null_bridge_refresh(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.refresh()
        assert result["ok"] is True
        assert result["peers"] == 0
        assert result["paired"] == 0

    def test_null_bridge_load_device_detail(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.loadDeviceDetail("test_key")
        assert result["ok"] is False

    def test_null_bridge_discover_devices(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.discoverDevices()
        assert result["ok"] is False
        assert result["error"] == "NO_DEVICE_SYNC_SERVICE"

    def test_null_bridge_pair_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.pairDevice("/media/test")
        assert result["ok"] is False

    def test_null_bridge_unpair_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.unpairDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_trust_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.trustDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_authorize_device(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.authorizeDevice("test_key")
        assert result["ok"] is False

    def test_null_bridge_start_transfer(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/t.flac", "/dst/t.flac")
        assert result["ok"] is False

    def test_null_bridge_cancel_transfer(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.cancelTransfer("job_1")
        assert result["ok"] is False

    def test_null_bridge_validate_audio(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.validateAudioFile("/music/track.flac")
        assert result["ok"] is True

    def test_null_bridge_eject(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.ejectDevice("/media/test")
        assert result["ok"] is False

    def test_empty_paired_devices(self, dev_svc):
        assert dev_svc.get_paired() == []

    def test_empty_discovered_devices(self, dev_svc):
        assert dev_svc.get_discovered() == []

    def test_empty_transfer_jobs(self, dev_svc):
        assert dev_svc.list_jobs() == []

    def test_empty_history(self, dev_svc):
        assert dev_svc.get_history() == []

    def test_empty_errors(self, dev_svc):
        assert dev_svc.last_errors() == []

    def test_identify_nonexistent(self, dev_svc):
        assert dev_svc.identify("/nonexistent") is None

    def test_video_file_rejected_by_validation(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.mp4")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_avi_video_rejected_by_validation(self, bridge, temp_music):
        path = str(temp_music / "Music" / "video.avi")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_unknown_format_rejected(self, bridge, temp_music):
        path = str(temp_music / "unknown.xyz")
        result = bridge.validateAudioFile(path)
        assert result["ok"] is False
        assert "UNSUPPORTED_FORMAT" in result.get("error", "")

    def test_transfer_no_service_returns_error(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/t.flac", "/dst/t.flac")
        assert result["ok"] is False

    def test_cancel_nonexistent_transfer(self, bridge):
        result = bridge.cancelTransfer("nonexistent_job")
        assert result["ok"] is False

    def test_retry_nonexistent_transfer(self, bridge):
        result = bridge.retryTransfer("nonexistent_job")
        assert result["ok"] is False

    def test_server_active_false_without_start(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.serverActive is False

    def test_peers_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.peers == []

    def test_paired_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.pairedDevices == []

    def test_discovered_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.discovered == []

    def test_transfer_jobs_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.transferJobs == []

    def test_transfer_history_empty_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.transferHistory == []

    def test_server_stop_before_start_returns_ok(self, mock_sync_mgr):
        bridge = DevicesBridge(sync_manager=mock_sync_mgr)
        result = bridge.stopServer()
        assert result["ok"] is True

    def test_storage_info_none_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.storageInfo == []

    def test_compatibility_info_none_without_service(self):
        bridge = DevicesBridge(sync_manager=None)
        assert bridge.compatibilityInfo == []


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = False
    return mgr


@pytest.fixture
def bridge(mock_sync_mgr):
    return DevicesBridge(sync_manager=mock_sync_mgr)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
