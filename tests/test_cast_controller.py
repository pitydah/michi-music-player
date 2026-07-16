"""Tests for CastController."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._ctx = MagicMock()
    w._ctx.transmit_mgr = MagicMock()
    w._ctx.player_bar = MagicMock()
    w._ctx.snapcast_ctrl = None
    w._ctx.ha_ctrl = None
    return w


@pytest.fixture
def ctrl(win):
    from legacy_widgets.ui.controllers.legacy_controllers.cast_controller import CastController
    return CastController(win)


class TestCastController:
    def test_init_sets_win_ctx_svc(self, ctrl, win):
        assert ctrl._win is win
        assert ctrl._ctx is win._ctx

    def test_show_cast_menu_no_ctx(self, ctrl):
        ctrl._ctx = None
        ctrl.show_cast_menu()

    def test_show_cast_menu_creates_menu(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu") as mock_menu_cls,
              patch("ui.premium_menus.premium_menu_qss") as mock_qss):
            mock_menu = mock_menu_cls.return_value
            mock_qss.return_value = "qss"
            win._ctx.transmit_mgr.get_active.return_value = None
            win._ctx.transmit_mgr.get_devices.return_value = []
            ctrl.show_cast_menu()
            mock_menu_cls.assert_called_once_with(win)
            mock_menu.setStyleSheet.assert_called_with("qss")

    def test_show_cast_menu_local_output_checked(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu"),
              patch("ui.premium_menus.premium_menu_qss")):
            win._ctx.transmit_mgr.get_active.return_value = None
            ctrl.show_cast_menu()

    def test_show_cast_menu_with_devices(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu"),
              patch("ui.premium_menus.premium_menu_qss")):
            dev = MagicMock()
            dev.name = "Speaker"
            dev.stype = "wifi"
            win._ctx.transmit_mgr.get_active.return_value = dev
            win._ctx.transmit_mgr.get_devices.return_value = [dev]
            ctrl.show_cast_menu()

    def test_show_cast_menu_with_snapcast_zones(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu"),
              patch("ui.premium_menus.premium_menu_qss")):
            sc = MagicMock()
            sc.get_zones.return_value = [{"id": "z1", "name": "Living", "active": True}]
            win._ctx.snapcast_ctrl = sc
            win._ctx.transmit_mgr.get_active.return_value = None
            win._ctx.transmit_mgr.get_devices.return_value = []
            ctrl.show_cast_menu()
            sc.get_zones.assert_called_once()

    def test_show_cast_menu_with_ha_devices(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu"),
              patch("ui.premium_menus.premium_menu_qss")):
            ha = MagicMock()
            ha.get_devices.return_value = [{"name": "Kitchen Speaker"}]
            win._ctx.ha_ctrl = ha
            win._ctx.transmit_mgr.get_active.return_value = None
            win._ctx.transmit_mgr.get_devices.return_value = []
            ctrl.show_cast_menu()
            ha.get_devices.assert_called_once()

    def test_show_cast_menu_without_player_bar(self, ctrl, win):
        with (patch("ui.controllers.cast_controller.QMenu"),
              patch("ui.premium_menus.premium_menu_qss")):
            del win._ctx.player_bar
            win._ctx.transmit_mgr.get_active.return_value = None
            win._ctx.transmit_mgr.get_devices.return_value = []
            ctrl.show_cast_menu()

    def test_transmit_device_selected_signal(self, ctrl):
        results = []
        ctrl.transmit_device_selected.connect(lambda d: results.append(d))
        ctrl.transmit_device_selected.emit(None)
        assert len(results) == 1
        assert results[0] is None

    def test_add_transmit_requested_signal(self, ctrl):
        results = []
        ctrl.add_transmit_requested.connect(lambda: results.append(True))
        ctrl.add_transmit_requested.emit()
        assert len(results) == 1

    def test_manage_transmit_requested_signal(self, ctrl):
        results = []
        ctrl.manage_transmit_requested.connect(lambda: results.append(True))
        ctrl.manage_transmit_requested.emit()
        assert len(results) == 1
