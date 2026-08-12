"""Tests for QtMultimediaBackend subscription semantics and media translation."""

import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer

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

    def test_accepted_duplicate_subscribe(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb(path):
            calls.append(path)

        b.subscribe_media_accepted(cb)
        b.subscribe_media_accepted(cb)
        assert len(b._acc) == 1

    def test_rejected_duplicate_subscribe(self, qapp):
        b = QtMultimediaBackend()
        calls = []

        def cb(path, msg):
            calls.append((path, msg))

        b.subscribe_media_rejected(cb)
        b.subscribe_media_rejected(cb)
        assert len(b._rej) == 1


class TestQtBackendMediaTranslation:
    """TD-008B: Qt media signals translate to app-level acceptance events."""

    def test_loaded_media_emits_accepted_with_current_source(self, qapp):
        b = QtMultimediaBackend()
        accepted = []
        b.subscribe_media_accepted(lambda p: accepted.append(p))
        b.load(Path("/tmp/song.mp3"))
        b._player.mediaStatusChanged.emit(QMediaPlayer.LoadedMedia)
        assert accepted == [Path("/tmp/song.mp3")]

    def test_invalid_media_emits_rejected(self, qapp):
        b = QtMultimediaBackend()
        rejected = []
        b.subscribe_media_rejected(lambda p, m: rejected.append((p, m)))
        b.load(Path("/tmp/broken.mp3"))
        b._player.mediaStatusChanged.emit(QMediaPlayer.InvalidMedia)
        assert rejected == [(Path("/tmp/broken.mp3"), "invalid media")]

    def test_error_occurred_emits_rejected(self, qapp):
        b = QtMultimediaBackend()
        rejected = []
        b.subscribe_media_rejected(lambda p, m: rejected.append((p, m)))
        b.load(Path("/tmp/broken.mp3"))
        b._player.errorOccurred.emit(QMediaPlayer.ResourceError, "cannot decode")
        assert rejected == [(Path("/tmp/broken.mp3"), "cannot decode")]

    def test_status_without_source_ignored(self, qapp):
        b = QtMultimediaBackend()
        accepted = []
        rejected = []
        b.subscribe_media_accepted(lambda p: accepted.append(p))
        b.subscribe_media_rejected(lambda p, m: rejected.append(m))
        b._player.mediaStatusChanged.emit(QMediaPlayer.LoadedMedia)
        b._player.mediaStatusChanged.emit(QMediaPlayer.InvalidMedia)
        assert accepted == []
        assert rejected == []
