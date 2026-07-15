from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.devices_bridge import (
    DevicesBridge,
    STATE_INITIALIZING,
    STATE_DISCOVERING,
    STATE_EMPTY,
    STATE_READY,
    STATE_PAIRING,
    STATE_PLANNING,
    STATE_TRANSFERRING,
    STATE_CANCELLING,
    STATE_PARTIAL_SUCCESS,
    STATE_ERROR,
    STATE_DEFERRED_PHYSICAL,
)

pytestmark = [pytest.mark.qml_module("devices")]


@pytest.fixture
def mock_dev_svc():
    svc = MagicMock()
    svc.discover.return_value = []
    svc.get_paired.return_value = []
    svc.running = False
    svc.peers = []
    return svc


@pytest.fixture
def bridge(mock_dev_svc):
    return DevicesBridge(
        device_sync_service=mock_dev_svc,
        job_service=MagicMock(),
        action_registry=MagicMock(),
        confirmation_service=MagicMock(),
        navigation_bridge=MagicMock(),
        capability_bridge=MagicMock(),
        page_state_store=MagicMock(),
        accessibility_bridge=MagicMock(),
    )


class TestDevicesCompletoStates:
    def test_initial_state(self, bridge):
        assert bridge.pageState == STATE_DISCOVERING

    def test_initializing_when_no_service(self):
        b = DevicesBridge()
        assert b.pageState == STATE_INITIALIZING

    def test_empty_when_server_active_no_devices(self, bridge):
        bridge._server_active = True
        bridge._set_state()
        assert bridge.pageState == STATE_EMPTY

    def test_ready_when_server_active_with_devices(self, bridge):
        bridge._server_active = True
        bridge._peers = [{"alias": "P1"}]
        bridge._set_state()
        assert bridge.pageState == STATE_READY

    def test_error_state(self):
        b = DevicesBridge()
        b.errorMessage = "Error"
        b._set_state()
        assert b.pageState == STATE_ERROR

    def test_deferred_physical(self):
        b = DevicesBridge()
        b.state = STATE_DEFERRED_PHYSICAL
        b.stateChanged.emit()
        assert b.pageState == STATE_DEFERRED_PHYSICAL


class TestDevicesCompletoDiscovery:
    def test_discover_returns_ok(self, bridge, mock_dev_svc):
        result = bridge.discover()
        assert result["ok"] is True

    def test_discover_no_service_fails(self):
        b = DevicesBridge()
        result = b.discover()
        assert result["ok"] is False

    def test_discover_populates_list(self, bridge, mock_dev_svc):
        mock_dev_svc.discover.return_value = [
            MagicMock(alias="Phone", device="android", ip="192.168.1.5", port=53318,
                      protocol="michi", serial="abc123"),
        ]
        result = bridge.discover()
        assert result["ok"] is True
        assert result["count"] == 1

    def test_discover_changes_state(self, bridge):
        assert bridge.pageState == STATE_DISCOVERING
        bridge.discover()

    def test_identify_no_service(self):
        b = DevicesBridge()
        result = b.identify("/media/usb")
        assert result["ok"] is False

    def test_identify_with_service(self, bridge, mock_dev_svc):
        mock_dev_svc.identify.return_value = "MTP:ABC123"
        result = bridge.identify("/media/usb")
        assert result["ok"] is True


class TestDevicesCompletoPairing:
    def test_pair_no_service(self):
        b = DevicesBridge()
        result = b.pairDevice("test_key")
        assert result["ok"] is False

    def test_pair_device_not_found(self, bridge, mock_dev_svc):
        mock_dev_svc.get_discovered.return_value = []
        result = bridge.pairDevice("test_key")
        assert result["ok"] is False

    def test_unpair_no_service(self):
        b = DevicesBridge()
        result = b.unpairDevice("key")
        assert result["ok"] is False

    def test_authorize_no_service(self):
        b = DevicesBridge()
        result = b.authorizeDevice("key")
        assert result["ok"] is False

    def test_trust_no_service(self):
        b = DevicesBridge()
        result = b.trustDevice("key")
        assert result["ok"] is False

    def test_pairing_sets_state(self, bridge, mock_dev_svc):
        mock_dev_svc.get_discovered.return_value = [MagicMock(protocol="michi", serial="abc", mount_point="/mnt")]
        mock_dev_svc.pair.return_value = {"ok": True}
        bridge.pairDevice("michi:abc")
        assert bridge.state in (STATE_PAIRING, STATE_READY, STATE_DISCOVERING)


class TestDevicesCompletoSync:
    def test_sync_plan_no_service(self):
        b = DevicesBridge()
        result = b.syncPlan("device1", "playlist:1")
        assert result["ok"] is False

    def test_estimate_no_service(self):
        b = DevicesBridge()
        result = b.estimate("device1", "playlist:1")
        assert result["ok"] is False

    def test_start_sync_no_service(self):
        b = DevicesBridge()
        result = b.startSync()
        assert result["ok"] is False

    def test_transfer_no_service(self):
        b = DevicesBridge()
        result = b.startTransfer("/src/test.flac", "/dst/")
        assert result["ok"] is False

    def test_transfer_video_rejected(self, bridge):
        result = bridge.startTransfer("/src/test.mp4", "/dst/")
        assert result["ok"] is False
        assert "VIDEO" in result["error"]

    def test_cancel_transfer_no_service(self):
        b = DevicesBridge()
        result = b.cancelTransfer("job_1")
        assert result["ok"] is False

    def test_retry_transfer_no_service(self):
        b = DevicesBridge()
        result = b.retryTransfer("job_1")
        assert result["ok"] is False

    def test_transfer_progress_no_service(self):
        b = DevicesBridge()
        result = b.transferProgress("job_1")
        assert result["ok"] is False

    def test_clear_history_no_service(self):
        b = DevicesBridge()
        result = b.clearTransferHistory()
        assert result["ok"] is True


class TestDevicesCompletoStorage:
    def test_storage_no_service(self):
        b = DevicesBridge()
        result = b.deviceDetailStorage("/mnt/device")
        assert result["ok"] is False

    def test_free_space_no_service(self):
        b = DevicesBridge()
        result = b.freeSpace("/mnt/device")
        assert result["ok"] is False

    def test_supported_formats_returns_audio(self, bridge):
        result = bridge.supportedFormats("/mnt/device")
        assert result["ok"] is True
        assert ".flac" in result["formats"]

    def test_compatibility_no_service(self):
        b = DevicesBridge()
        result = b.deviceDetailCompatibility("/mnt/device")
        assert result["ok"] is False

    def test_selection_returns_ok(self, bridge):
        result = bridge.selection("sel_1")
        assert result["ok"] is True

    def test_transcode_policy_no_service(self):
        b = DevicesBridge()
        result = b.transcodePolicy("device1")
        assert result["ok"] is False

    def test_naming_no_service(self):
        b = DevicesBridge()
        result = b.naming("device1", "{artist}/{album}/{track}")
        assert result["ok"] is False

    def test_collision_no_service(self):
        b = DevicesBridge()
        result = b.collision("device1", "rename")
        assert result["ok"] is False


class TestDevicesCompletoProfile:
    def test_profile_no_service(self):
        b = DevicesBridge()
        result = b.profile("device1")
        assert result["ok"] is False

    def test_load_device_detail_no_service(self):
        b = DevicesBridge()
        result = b.loadDeviceDetail("device1")
        assert result["ok"] is False

    def test_load_device_detail_no_key(self, bridge):
        result = bridge.loadDeviceDetail("")
        assert result["ok"] is False


class TestDevicesCompletoEject:
    def test_eject_no_service(self):
        b = DevicesBridge()
        result = b.ejectDevice("/mnt/device")
        assert result["ok"] is False

    def test_eject_no_mount_point(self, bridge):
        result = bridge.ejectDevice("")
        assert result["ok"] is False

    def test_eject_with_service(self, bridge, mock_dev_svc):
        mock_dev_svc.eject.return_value = True
        result = bridge.ejectDevice("/mnt/device")
        assert result["ok"] is True


class TestDevicesCompletoHistory:
    def test_history_no_service(self):
        b = DevicesBridge()
        result = b.history("device1")
        assert result["ok"] is False

    def test_history_with_service(self, bridge, mock_dev_svc):
        mock_dev_svc.get_history.return_value = [{"job_id": "1", "status": "completed"}]
        result = bridge.history("device1")
        assert result["ok"] is True


class TestDevicesCompletoValidate:
    def test_validate_audio_file(self, bridge):
        result = bridge.validateAudioFile("/music/test.flac")
        assert result["ok"] is True
        assert result["type"] == "audio"

    def test_validate_video_file_rejected(self, bridge):
        result = bridge.validateAudioFile("/music/test.mp4")
        assert result["ok"] is False
        assert "VIDEO" in result["error"]

    def test_validate_unsupported_format(self, bridge):
        result = bridge.validateAudioFile("/music/test.xyz")
        assert result["ok"] is False

    def test_validate_nonexistent_file_audio(self, bridge):
        result = bridge.validateAudioFile("/nonexistent/test.flac")
        assert result["ok"] is True
        assert result.get("warning") == "FILE_NOT_FOUND"


class TestDevicesCompletoDeviceIcon:
    def test_device_icon_known_types(self):
        b = DevicesBridge()
        assert b.getDeviceIcon("android") == "smartphone"
        assert b.getDeviceIcon("ums") == "usb"
        assert b.getDeviceIcon("mtp") == "smartphone"
        assert b.getDeviceIcon("michi") == "devices"
        assert b.getDeviceIcon("generic") == "folder"

    def test_device_icon_unknown(self):
        b = DevicesBridge()
        assert b.getDeviceIcon("unknown") == "devices"


class TestDevicesCompletoQR:
    def test_generate_qr_code(self, bridge):
        qr = bridge.generateQRCode()
        assert qr.startswith("michi://pair/")
        assert bridge.qrCodeData == qr

    def test_qr_code_unique(self, bridge):
        qr1 = bridge.generateQRCode()
        qr2 = bridge.generateQRCode()
        assert qr1 != qr2


class TestDevicesCompletoFileName:
    def test_file_name_returns_basename(self, bridge):
        assert bridge.fileName("/path/to/file.flac") == "file.flac"

    def test_file_name_empty(self, bridge):
        assert bridge.fileName("") == ""


class TestDevicesCompletoRefresh:
    def test_refresh_no_service(self):
        b = DevicesBridge()
        result = b.refresh()
        assert result["ok"] is True

    def test_refresh_with_service(self, bridge, mock_dev_svc):
        mock_dev_svc.get_all_peers.return_value = [{"alias": "Phone"}]
        mock_dev_svc.get_paired_devices.return_value = [{"alias": "Laptop"}]
        mock_dev_svc.is_active = True
        result = bridge.refresh()
        assert result["ok"] is True
        assert result["peers"] == 1
        assert result["paired"] == 1
