"""Test negative/edge cases: null bridge, empty states, errors."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.device_sync_service import DeviceSyncService, DeviceIdentity, DeviceProtocol
from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


class TestNullBridge:
    def test_bridge_none(self):
        b = DevicesBridge(sync_manager=None)
        assert b._sync_mgr is None
        assert b.bridgeAvailable is True

    def test_start_server_null(self):
        b = DevicesBridge()
        result = b.startServer()
        assert result["ok"] is False
        assert "NO_SYNC_MANAGER" in result.get("error", "")

    def test_stop_server_null(self):
        b = DevicesBridge()
        result = b.stopServer()
        assert result["ok"] is False

    def test_refresh_null(self):
        b = DevicesBridge()
        result = b.refresh()
        assert result["ok"] is True
        assert result["peers"] == 0

    def test_discover_null(self):
        b = DevicesBridge()
        result = b.discoverDevices()
        assert result["ok"] is False

    def test_pair_null(self):
        b = DevicesBridge()
        result = b.pairDevice("/media/test")
        assert result["ok"] is False

    def test_unpair_null(self):
        b = DevicesBridge()
        result = b.unpairDevice("key")
        assert result["ok"] is False

    def test_detail_storage_null(self):
        b = DevicesBridge()
        result = b.deviceDetailStorage("/media/test")
        assert result["ok"] is False

    def test_detail_compat_null(self):
        b = DevicesBridge()
        result = b.deviceDetailCompatibility("/media/test")
        assert result["ok"] is False

    def test_transfer_null(self):
        b = DevicesBridge()
        result = b.startTransfer("/src.flac", "/dst.flac")
        assert result["ok"] is False

    def test_cancel_null(self):
        b = DevicesBridge()
        result = b.cancelTransfer("job-1")
        assert result["ok"] is False

    def test_retry_null(self):
        b = DevicesBridge()
        result = b.retryTransfer("job-1")
        assert result["ok"] is False

    def test_trust_null(self):
        b = DevicesBridge()
        result = b.trustDevice("key")
        assert result["ok"] is False

    def test_eject_null(self):
        b = DevicesBridge()
        result = b.ejectDevice("/media/test")
        assert result["ok"] is False

    def test_connect_null(self):
        b = DevicesBridge()
        result = b.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is False


class TestEmptyStates:
    def test_no_peers(self):
        mgr = MagicMock()
        mgr.get_all_peers.return_value = []
        mgr.is_active = True
        b = DevicesBridge(sync_manager=mgr)
        b.refresh()
        assert b.peers == []

    def test_no_paired(self):
        mgr = MagicMock()
        mgr.get_paired_devices.return_value = []
        b = DevicesBridge(sync_manager=mgr)
        b.refresh()
        assert b.pairedDevices == []

    def test_no_discovered(self):
        svc = MagicMock()
        svc.discover.return_value = []
        b = DevicesBridge(device_sync_service=svc)
        b.discoverDevices()
        assert b.discovered == []

    def test_no_transfer_jobs(self):
        b = DevicesBridge()
        assert b.transferJobs == []

    def test_no_transfer_history(self):
        b = DevicesBridge()
        assert b.transferHistory == []

    def test_no_storage_info(self):
        b = DevicesBridge()
        assert b.storageInfo == []

    def test_no_compatibility_info(self):
        b = DevicesBridge()
        assert b.compatibilityInfo == []

    def test_empty_qr(self):
        b = DevicesBridge()
        assert b.qrCodeData == ""


class TestErrorStates:
    def test_error_state_on_exception(self, tmp_path):
        mgr = MagicMock()
        mgr.start.side_effect = RuntimeError("Connection lost")
        b = DevicesBridge(sync_manager=mgr)
        result = b.startServer()
        assert result["ok"] is False
        assert "Connection lost" in result.get("error", "")

    def test_error_on_refresh_exception(self):
        mgr = MagicMock()
        mgr.get_all_peers.side_effect = RuntimeError("DB locked")
        b = DevicesBridge(sync_manager=mgr)
        result = b.refresh()
        assert result["ok"] is True

    def test_pair_not_found(self):
        svc = MagicMock()
        svc.identify.return_value = None
        b = DevicesBridge(device_sync_service=svc)
        result = b.pairDevice("/nonexistent")
        assert result["ok"] is False
        assert result.get("error") == "NOT_FOUND"

    def test_unpair_not_paired(self):
        svc = DeviceSyncService()
        b = DevicesBridge(device_sync_service=svc)
        result = b.unpairDevice("nonexistent")
        assert result["ok"] is False

    def test_transfer_missing_file(self, tmp_path):
        svc = DeviceSyncService()
        b = DevicesBridge(device_sync_service=svc)
        result = b.startTransfer(
            str(tmp_path / "missing.flac"),
            str(tmp_path / "out.flac"),
        )
        assert result["ok"] is False

    def test_transfer_video_rejected(self, tmp_path):
        svc = DeviceSyncService()
        b = DevicesBridge(device_sync_service=svc)
        result = b.startTransfer(
            str(tmp_path / "video.mp4"),
            str(tmp_path / "out.mp4"),
        )
        assert result["ok"] is False
        assert "VIDEO" in str(result).upper()

    def test_cancel_nonexistent(self):
        svc = DeviceSyncService()
        b = DevicesBridge(device_sync_service=svc)
        result = b.cancelTransfer("no-such-job")
        assert result["ok"] is False

    def test_retry_nonexistent(self):
        svc = DeviceSyncService()
        b = DevicesBridge(device_sync_service=svc)
        result = b.retryTransfer("no-such-job")
        assert result["ok"] is False

    def test_validate_nonexistent_ext(self):
        b = DevicesBridge()
        result = b.validateAudioFile("/nonexistent.xyz")
        assert result["ok"] is False


class TestEdgeCases:
    def test_duplicate_pair(self):
        svc = DeviceSyncService()
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="dup",
            mount_point="/media/dup",
        )
        svc.pair(identity)
        result = svc.pair(identity)
        assert result["ok"] is False
        assert result["error"] == "ALREADY_PAIRED"

    def test_unpair_twice(self):
        svc = DeviceSyncService()
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Player", serial="double",
            mount_point="/media/double",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        svc.unpair(key)
        result = svc.unpair(key)
        assert result["ok"] is False

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
