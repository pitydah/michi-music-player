"""Test: radio service operations."""


class TestRadioService:
    def test_radio_service_import(self):
        from core.radio.service import RadioService
        assert RadioService is not None


class TestRadioBridge:
    def test_radio_bridge_import(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert RadioBridge is not None
        assert hasattr(RadioBridge, 'dataChanged')

    def test_radio_bridge_has_slots(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert hasattr(RadioBridge, 'addStation')
        assert hasattr(RadioBridge, 'search')
