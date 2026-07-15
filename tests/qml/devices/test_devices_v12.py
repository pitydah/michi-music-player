"""Tests for Devices v12 — contractual, no _normalise_result(None) -> ok True.
Estados: INITIALIZING..DEFERRED_PHYSICAL. Audio-only."""
from unittest.mock import MagicMock

import pytest


class TestDevicesBridgeCreation:
    def test_requires_device_sync(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        with pytest.raises(Exception):
            DevicesBridge()

    def test_requires_job_service(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        with pytest.raises(Exception):
            DevicesBridge(device_sync_service=MagicMock())

    def test_creation(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        assert db is not None

    def test_initial_state(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        assert db.pageState in ("INITIALIZING", "DISCOVERING", "READY", "EMPTY", "DEFERRED_PHYSICAL")

    def test_bridge_available(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        assert isinstance(db.bridgeAvailable, bool)


class TestDevicesOperations:
    def test_refresh(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        result = db.refresh()
        assert isinstance(result, dict)

    def test_discover(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        result = db.discover()
        assert isinstance(result, dict)

    def test_start_server(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        svc = MagicMock()
        svc.start.return_value = {"ok": True}
        db = DevicesBridge(device_sync_service=svc, job_service=MagicMock())
        result = db.startServer()
        assert isinstance(result, dict)

    def test_stop_server(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        svc = MagicMock()
        svc.stop.return_value = {"ok": True}
        db = DevicesBridge(device_sync_service=svc, job_service=MagicMock())
        result = db.stopServer()
        assert isinstance(result, dict)

    def test_no_video_support(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        svc = MagicMock()
        svc.create_transfer_job.return_value = MagicMock()
        db = DevicesBridge(device_sync_service=svc, job_service=MagicMock())
        result = db.startTransfer("/test/video.mp4", "/dest")
        assert not result.get("ok")

    def test_audio_only_supported(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        format_result = db.validateAudioFile("/test/file.mp3")
        assert format_result.get("ok")
        assert format_result.get("type") == "audio"

    def test_file_name(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        name = db.fileName("/path/to/file.flac")
        assert name == "file.flac"

    def test_generate_qr_code(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        code = db.generateQRCode()
        assert code.startswith("michi://pair/")

    def test_transfer_active_default(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        assert db.transferActive is False

    def test_history(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        svc = MagicMock()
        svc.get_history.return_value = []
        db = DevicesBridge(device_sync_service=svc, job_service=MagicMock())
        result = db.history()
        assert isinstance(result, dict)

    def test_clear_transfer_history(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        result = db.clearTransferHistory()
        assert result.get("ok")

    def test_normalise_result_none(self):
        from ui_qml_bridge.devices_bridge import _normalise_result
        result = _normalise_result(None)
        assert not result.get("ok")

    def test_get_device_icon(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge(device_sync_service=MagicMock(), job_service=MagicMock())
        icon = db.getDeviceIcon("android")
        assert icon == "smartphone"
