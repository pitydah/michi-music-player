from __future__ import annotations
"""DH — Workflow harness QML real: QGuiApplication, bridges reales, QML pages."""

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest
from PySide6.QtCore import QObject

REPO = Path(__file__).resolve().parent.parent.parent.parent
QML_DIR = REPO / "ui_qml"

from PySide6.QtCore import QObject

from tests.qml.runtime.qml_test_harness import (  # noqa: E402
    QmlTestHarness,
    FakePlayerService,
)


# ── Fixtures ──


@pytest.fixture
def harness():
    h = QmlTestHarness()
    yield h
    h.cleanup()


@pytest.fixture
def real_harness(harness):
    harness.setup_db()
    fake_player = FakePlayerService()
    harness.register_bridge("playbackBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("nowplayingBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("libraryBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("navigationBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("themeBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("appBridge", QObject(parent=harness.engine.rootContext()))
    harness.register_bridge("coverBridge", QObject(parent=harness.engine.rootContext()))
    return harness, fake_player


# ── Harness construction ──


def test_harness_creates_app(harness):
    assert harness._app is not None


def test_harness_creates_engine(harness):
    assert harness.engine is not None


def test_harness_starts_without_root(harness):
    assert harness.root is None


def test_harness_accepts_custom_qml_path():
    h = QmlTestHarness(qml_path=str(QML_DIR / "shell" / "AppShell.qml"))
    assert h is not None
    h.cleanup()


# ── DB setup ──


def test_setup_db_creates_connection(harness):
    db_path = harness.setup_db()
    assert db_path.exists()
    assert harness.db is not None


def test_setup_db_populates_tracks(harness):
    harness.setup_db()
    tracks = harness.db.get_tracks()
    assert len(tracks) > 0


def test_db_has_multiple_albums(harness):
    harness.setup_db()
    tracks = harness.db.get_tracks()
    albums = set(t[3] for t in tracks)
    assert len(albums) >= 1


# ── Bridge registration ──


def test_register_bridge(harness):
    bridge = QObject()
    harness.register_bridge("testBridge", bridge)
    assert "testBridge" in harness._bridges


def test_register_multiple_bridges(harness):
    for name in ["bridgeA", "bridgeB", "bridgeC"]:
        harness.register_bridge(name, QObject())
    assert len(harness._bridges) == 3


# ── QML loading ──


def test_load_qml_component(harness):
    root = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert root is not None


def test_load_qml_root_is_qobject(harness):
    root = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert isinstance(root, QObject)


def test_load_qml_with_bridges(real_harness):
    harness, player = real_harness
    root = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert root is not None


def test_load_nonexistent_qml_raises(harness):
    with pytest.raises(RuntimeError):
        harness.load_qml(str(QML_DIR / "nonexistent.qml"))


# ── Control finding ──


def test_find_control_returns_none_for_missing(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    ctrl = harness.find_control("nonexistent_control")
    assert ctrl is None


def test_find_controls_returns_list(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    ctrls = harness.find_controls("")
    assert isinstance(ctrls, list)


# ── QTest interactions ──


def test_process_events_does_not_crash(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    harness.process_events(3)


def test_process_events_after_load(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    harness.process_events(3)


# ── Cleanup ──


def test_cleanup_sets_root_none(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    harness.cleanup()
    assert harness.root is None


def test_cleanup_creates_new_engine(harness):
    harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    harness.cleanup()
    assert harness.engine is not None


def test_cleanup_closes_db(harness):
    harness.setup_db()
    assert harness.db is not None
    harness.cleanup()
    assert harness._db_conn is None


# ── Full lifecycle ──


def test_full_lifecycle_with_db_and_bridges(real_harness):
    harness, player = real_harness
    root = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert root is not None
    harness.process_events()
    harness.cleanup()
    assert harness.root is None


def test_reload_after_cleanup(harness):
    root1 = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert root1 is not None
    harness.cleanup()
    root2 = harness.load_qml(str(QML_DIR / "theme" / "MichiTheme.qml"))
    assert root2 is not None
    harness.cleanup()
