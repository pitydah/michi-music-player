"""Tests for MPRIS CanQuit/CanRaise correctness.

CanQuit is only True when Quit() actually works (a quit handler is wired);
CanRaise is only True when Raise() works (a raise handler is wired). The
desktop must never be promised a no-op.
"""
from __future__ import annotations

import pytest

pytest.importorskip("dbus")


def _make_object():
    """Build an MPRISObject bypassing the dbus bus registration in __init__."""
    from adapters.mpris import MPRISObject

    obj = object.__new__(MPRISObject)
    obj._engine = None
    obj._player_service = None
    obj._queue_service = None
    obj._metadata = {}
    obj._volume = 0.7
    obj._quit_handler = None
    obj._raise_handler = None
    return obj


class TestCanQuitCanRaise:
    def test_defaults_are_false_when_no_handlers(self):
        obj = _make_object()
        props = obj.GetAll("org.mpris.MediaPlayer2")
        assert props["CanQuit"] is False
        assert props["CanRaise"] is False

    def test_can_quit_true_only_when_handler_wired(self):
        obj = _make_object()
        obj.set_quit_handler(lambda: None)
        props = obj.GetAll("org.mpris.MediaPlayer2")
        assert props["CanQuit"] is True
        assert props["CanRaise"] is False

    def test_can_raise_true_only_when_handler_wired(self):
        obj = _make_object()
        obj.set_raise_handler(lambda: None)
        props = obj.GetAll("org.mpris.MediaPlayer2")
        assert props["CanRaise"] is True
        assert props["CanQuit"] is False

    def test_quit_calls_wired_handler(self):
        obj = _make_object()
        called = []
        obj.set_quit_handler(lambda: called.append(True))
        obj.Quit()
        assert called == [True]

    def test_raise_calls_wired_handler(self):
        obj = _make_object()
        called = []
        obj.set_raise_handler(lambda: called.append(True))
        obj.Raise()
        assert called == [True]

    def test_quit_is_noop_without_handler(self):
        obj = _make_object()
        obj.Quit()  # must not raise

    def test_raise_is_noop_without_handler(self):
        obj = _make_object()
        obj.Raise()  # must not raise

    def test_clearing_handler_disables_can_quit(self):
        obj = _make_object()
        obj.set_quit_handler(lambda: None)
        assert obj.GetAll("org.mpris.MediaPlayer2")["CanQuit"] is True
        obj.set_quit_handler(None)
        assert obj.GetAll("org.mpris.MediaPlayer2")["CanQuit"] is False

    def test_clearing_handler_disables_can_raise(self):
        obj = _make_object()
        obj.set_raise_handler(lambda: None)
        assert obj.GetAll("org.mpris.MediaPlayer2")["CanRaise"] is True
        obj.set_raise_handler(None)
        assert obj.GetAll("org.mpris.MediaPlayer2")["CanRaise"] is False
