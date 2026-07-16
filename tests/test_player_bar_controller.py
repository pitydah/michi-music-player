"""Tests for PlayerBarController — requires NowPlayingBar via pytest-qt."""
from ui.nowplaying_bar import NowPlayingBar
from ui.controllers.player_bar_controller import PlayerBarController


def test_init(qtbot):
    bar = NowPlayingBar()
    qtbot.addWidget(bar)
    ctrl = PlayerBarController(bar)
    assert ctrl._player_bar is bar


def test_set_track(qtbot):
    bar = NowPlayingBar()
    qtbot.addWidget(bar)
    ctrl = PlayerBarController(bar)
    ctrl.set_track("Test Song", "Test Artist", "")
    # Should not crash


def test_reset(qtbot):
    bar = NowPlayingBar()
    qtbot.addWidget(bar)
    ctrl = PlayerBarController(bar)
    ctrl.reset()
    # Should set stopped state


def test_volume_operations(qtbot):
    bar = NowPlayingBar()
    qtbot.addWidget(bar)
    ctrl = PlayerBarController(bar)
    assert ctrl.volume_value() >= 0
    ctrl.change_volume(5)
    ctrl.mute()
