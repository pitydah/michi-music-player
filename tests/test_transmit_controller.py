"""Tests for TransmitController."""
from legacy_widgets.ui.controllers.legacy_controllers.transmit_controller import TransmitController


class TestTransmitController:
    def test_activate_none(self, mock_window):
        ctrl = TransmitController(mock_window)
        ctrl.activate_device(None)
        mock_window._transmit_mgr.set_active.assert_called_with(None)
        mock_window._playback.set_transmit_device.assert_called_with(None)

    def test_active_changed_none(self, mock_window):
        mock_window._transmit_mgr.get_active.return_value = None
        ctrl = TransmitController(mock_window)
        ctrl.on_active_changed()
        mock_window._player_bar_ctrl.set_transmit_active.assert_called_with(False)
