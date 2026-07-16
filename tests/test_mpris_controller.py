"""Tests for MPRISController."""
from legacy_widgets.ui.controllers.legacy_controllers.mpris_controller import MPRISController


class TestMPRISController:
    def test_init_no_dbus(self, mock_window):
        ctrl = MPRISController(mock_window)
        ctrl.init()
        # Without DBus, adapter should be None
        assert ctrl.adapter is None
        assert not ctrl.is_active

    def test_update_metadata_no_adapter(self, mock_window):
        ctrl = MPRISController(mock_window)
        ctrl.update_metadata("Title", "Artist", "Album", 240)
        # Should not crash without adapter
