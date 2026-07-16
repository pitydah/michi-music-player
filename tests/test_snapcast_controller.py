"""Tests for SnapcastController."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._ctx = MagicMock()
    w._ctx.snapserver = MagicMock()
    w._ctx.audio_capture = MagicMock()
    w._ctx.group_mgr = MagicMock()
    w._ctx.player_bar = MagicMock()
    w._ctx.toast = MagicMock()
    return w


@pytest.fixture
def ctrl(win):
    from legacy_widgets.ui.controllers.legacy_controllers.snapcast_controller import SnapcastController
    c = SnapcastController.__new__(SnapcastController)
    from PySide6.QtCore import QObject
    QObject.__init__(c)
    c._win = win
    c._ctx = win._ctx
    c._svc = None
    return c


class TestSnapcastController:
    def test_init_sets_win_ctx(self, ctrl, win):
        assert ctrl._win is win
        assert ctrl._ctx is win._ctx

    def test_activate_zone_starts_snapserver(self, ctrl, win):
        win._ctx.snapserver.is_running = False
        win._ctx.snapserver.is_binary_available.return_value = True
        group = {"id": "z1", "name": "Living"}
        ctrl.activate_zone(group)
        win._ctx.audio_capture.create_sink.assert_called_once()
        win._ctx.group_mgr.activate_group.assert_called_with("z1")
        win._ctx.player_bar.set_transmit_active.assert_called_with(True, "Living")
        win._ctx.toast.show.assert_called_once()

    def test_activate_zone_already_running(self, ctrl, win):
        win._ctx.snapserver.is_running = True
        group = {"id": "z1", "name": "Living"}
        ctrl.activate_zone(group)
        win._ctx.audio_capture.create_sink.assert_not_called()
        win._ctx.group_mgr.activate_group.assert_called_with("z1")

    def test_activate_zone_no_snapserver(self, ctrl, win):
        win._ctx.snapserver = None
        group = {"id": "z1"}
        ctrl.activate_zone(group)
        win._ctx.group_mgr.activate_group.assert_called_with("z1")

    def test_activate_zone_no_snapserver_no_capture(self, ctrl, win):
        win._ctx.snapserver = MagicMock()
        win._ctx.snapserver.is_running = False
        win._ctx.snapserver.is_binary_available.return_value = False
        group = {"id": "z1"}
        ctrl.activate_zone(group)
        win._ctx.audio_capture.create_sink.assert_not_called()
        win._ctx.group_mgr.activate_group.assert_called_with("z1")

    def test_activate_zone_no_player_bar(self, ctrl, win):
        win._ctx.player_bar = None
        group = {"id": "z1", "name": "Living"}
        ctrl.activate_zone(group)
        win._ctx.group_mgr.activate_group.assert_called_with("z1")

    def test_activate_zone_emits_signal(self, ctrl, win):
        results = []
        ctrl.zone_activated.connect(lambda i, n: results.append((i, n)))
        ctrl.activate_zone({"id": "z1", "name": "Living"})
        assert results == [("z1", "Living")]

    def test_get_zones_returns_groups(self, ctrl, win):
        win._ctx.group_mgr.groups.return_value = [{"id": "z1"}]
        zones = ctrl.get_zones()
        assert zones == [{"id": "z1"}]

    def test_get_zones_returns_empty_without_group_mgr(self, ctrl, win):
        win._ctx.group_mgr = None
        assert ctrl.get_zones() == []
