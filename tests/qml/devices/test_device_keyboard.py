"""Test keyboard navigation for Devices pages."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


class TestDeviceKeyboardNavigation:
    def test_connect_to_peer_slot(self):
        mgr = MagicMock()
        mgr.connect.return_value = {"ok": True}
        b = DevicesBridge(sync_manager=mgr)
        result = b.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is True

    def test_start_stop_server(self):
        mgr = MagicMock()
        mgr.start.return_value = True
        mgr.stop.return_value = True
        b = DevicesBridge(sync_manager=mgr)
        assert b.startServer()["ok"] is True
        assert b.stopServer()["ok"] is True

    def test_discover_devices(self):
        svc = MagicMock()
        svc.discover.return_value = []
        b = DevicesBridge(device_sync_service=svc)
        result = b.discoverDevices()
        assert result["ok"] is True

    def test_pair_device_slot(self):
        svc = MagicMock()
        identity = MagicMock()
        svc.identify.return_value = identity
        svc.pair.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.pairDevice("/media/test")
        assert result["ok"] is True

    def test_unpair_device_slot(self):
        svc = MagicMock()
        svc.unpair.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.unpairDevice("test-key")
        assert result["ok"] is True

    def test_refresh_slot(self):
        mgr = MagicMock()
        b = DevicesBridge(sync_manager=mgr)
        result = b.refresh()
        assert result["ok"] is True

    def test_generate_qr_slot(self):
        b = DevicesBridge()
        qr = b.generateQRCode()
        assert isinstance(qr, str)
        assert qr.startswith("michi://pair/")

    def test_trust_device_slot(self):
        svc = MagicMock()
        svc.trust.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.trustDevice("test-key")
        assert result["ok"] is True

    def test_cancel_transfer_slot(self):
        svc = MagicMock()
        svc.cancel_job.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.cancelTransfer("job-1")
        assert result["ok"] is True

    def test_retry_transfer_slot(self):
        svc = MagicMock()
        svc.retry_job.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.retryTransfer("job-1")
        assert result["ok"] is True

    def test_validate_audio_slot(self):
        b = DevicesBridge()
        result = b.validateAudioFile("/music/track.flac")
        assert result["ok"] is False  # File doesn't exist

    def test_eject_device_slot(self):
        svc = MagicMock()
        svc.eject.return_value = True
        b = DevicesBridge(device_sync_service=svc)
        result = b.ejectDevice("/media/test")
        assert result["ok"] is True

    def test_browse_files_slot(self):
        svc = MagicMock()
        svc.list_music.return_value = [{"name": "track.flac"}]
        b = DevicesBridge(device_sync_service=svc)
        result = b.browseFiles("/media/test", "Music")
        assert result["ok"] is True
        assert len(result["files"]) == 1

    def test_get_device_icon_slot(self):
        b = DevicesBridge()
        icon = b.getDeviceIcon("android")
        assert isinstance(icon, str)
        assert icon == "smartphone"

    def test_clear_history_slot(self):
        svc = MagicMock()
        b = DevicesBridge(device_sync_service=svc)
        result = b.clearTransferHistory()
        assert result["ok"] is True
