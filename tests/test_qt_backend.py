"""Tests for QtMultimediaBackend subscription semantics."""

import sys

import pytest
from PySide6.QtGui import QGuiApplication

from michi.infrastructure.qt_backend import QtMultimediaBackend


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQtBackendSubscriptions:
    def test_duplicate_subscribe_does_not_double_connect(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb():
            calls.append(1)

        b.subscribe_end_of_media(cb)
        b.subscribe_end_of_media(cb)
        assert len(b._eom) == 1

    def test_double_unsubscribe_is_safe(self, qapp):
        b = QtMultimediaBackend()

        def cb():
            pass

        b.subscribe_end_of_media(cb)
        b.unsubscribe_end_of_media(cb)
        b.unsubscribe_end_of_media(cb)
        assert len(b._eom) == 0

    def test_multiple_subscribers_independent(self, qapp):
        b = QtMultimediaBackend()
        ca_calls = []
        cb_calls = []

        def ca():
            ca_calls.append(1)

        def cb():
            cb_calls.append(1)

        b.subscribe_end_of_media(ca)
        b.subscribe_end_of_media(cb)
        assert len(b._eom) == 2
        b.unsubscribe_end_of_media(ca)
        assert len(b._eom) == 1
        b.unsubscribe_end_of_media(cb)
        assert len(b._eom) == 0

    def test_position_duplicate_subscribe(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb(pos):
            calls.append(pos)

        b.subscribe_position_changed(cb)
        b.subscribe_position_changed(cb)
        assert len(b._pos) == 1

    def test_duration_duplicate_subscribe(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb(dur):
            calls.append(dur)

        b.subscribe_duration_changed(cb)
        b.subscribe_duration_changed(cb)
        assert len(b._dur) == 1

    def test_error_duplicate_subscribe(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb(msg):
            calls.append(msg)

        b.subscribe_error(cb)
        b.subscribe_error(cb)
        assert len(b._err) == 1
