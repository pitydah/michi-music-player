from unittest.mock import MagicMock
from ui_qml_bridge.devices_bridge import DevicesBridge


class TestDevicesBridge:
    def test_create(self):
        bridge = DevicesBridge(sync_manager=MagicMock(), device_registry=MagicMock())
        assert bridge is not None
