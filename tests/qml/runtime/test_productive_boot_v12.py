from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QQmlApplicationEngine

REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))

from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ContainerState

NAV_ROUTES = ["home", "library", "playback", "home_audio", "connections", "queue", "radio", "playlists", "ai"]


@pytest.fixture(scope="module")
def app():
    a = QGuiApplication.instance()
    if not a:
        a = QGuiApplication(sys.argv)
    return a


@pytest.fixture(scope="module")
def engine():
    e = QQmlApplicationEngine()
    e.addImportPath(str(REPO / "ui_qml"))
    return e


def _create_app():
    a = QGuiApplication.instance()
    if not a:
        a = QGuiApplication(sys.argv)
    return a


def test_1_create_qgui_application(app):
    assert QGuiApplication.instance() is not None


def test_2_create_qqml_application_engine(engine):
    assert isinstance(engine, QQmlApplicationEngine)


def test_3_application_bootstrap_build():
    b = ApplicationBootstrap()
    b.build()
    assert b.container is not None


def test_4_container_validate():
    b = ApplicationBootstrap()
    b.build()
    missing = b.container.validate_required_present()
    assert missing == [], f"REQUIRED services missing: {missing}"
    none_req = b.container.validate_no_none_required()
    assert none_req == [], f"REQUIRED services are None: {none_req}"


def test_5_container_start():
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    assert b.container.state in (ContainerState.READY, ContainerState.DEGRADED), f"Container state={b.container.state.value}"


def test_6_bridge_factory_create_all():
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    bridges = b.create_bridges()
    assert isinstance(bridges, dict)
    assert "navigation" in bridges
    assert "theme" in bridges
    assert "app" in bridges


def test_7_context_registrar_register():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    registrar = b.register_context(engine)
    audit = registrar.audit()
    assert audit["total"] > 0
    assert audit["violations"] == [], f"Context violations: {audit['violations']}"


def test_8_engine_load_main_qml():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    b.register_context(engine)
    ok = b.load_qml(engine)
    assert ok, "Main.qml could not be loaded"
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "No root objects in engine"


def test_9_root_objects_present():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    b.register_context(engine)
    b.load_qml(engine)
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0
    win = root_objects[0]
    assert win is not None


def test_10_navigate_routes_via_navigation_bridge():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    b.register_context(engine)
    b.load_qml(engine)
    ctx = engine.rootContext()
    nav = ctx.contextProperty("navigationBridge") if ctx else None
    assert nav is not None, "navigationBridge not in context"
    for r in NAV_ROUTES:
        nav.navigate(r)
        QCoreApplication.processEvents()
        cur = getattr(nav, 'currentRoute', None)
        assert cur is not None


def test_11_process_events():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    b.register_context(engine)
    b.load_qml(engine)
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()


def test_12_shutdown():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))
    b = ApplicationBootstrap()
    b.build()
    b.container.start()
    b.create_bridges()
    b.register_context(engine)
    b.load_qml(engine)
    b.shutdown()
    assert b.container.state == ContainerState.STOPPED


def test_full_productive_boot():
    app = _create_app()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO / "ui_qml"))

    bootstrap = ApplicationBootstrap()
    bootstrap.build()

    container = bootstrap.container
    missing = container.validate_required_present()
    assert missing == [], f"REQUIRED services missing: {missing}"
    none_req = container.validate_no_none_required()
    assert none_req == [], f"REQUIRED services are None: {none_req}"

    container.start()
    assert container.state in (ContainerState.READY, ContainerState.DEGRADED), f"Container state={container.state.value}"

    bridges = bootstrap.create_bridges()
    assert "navigation" in bridges
    assert "theme" in bridges

    registrar = bootstrap.register_context(engine)
    audit = registrar.audit()
    assert audit["total"] > 0
    assert audit["violations"] == []

    ok = bootstrap.load_qml(engine)
    assert ok

    root_objects = engine.rootObjects()
    assert len(root_objects) > 0
    win = root_objects[0]

    def _walk_children(obj, max_depth=5):
        items = []
        def _walk(o, d):
            if d > max_depth:
                return
            items.append(o)
            for c in o.children():
                _walk(c, d + 1)
        _walk(obj, 0)
        return items
    all_obs = _walk_children(win, max_depth=6)
    assert len(all_obs) > 10, "AppShell tree too small — AppShell likely not instantiated"

    ctx = engine.rootContext()
    nav = ctx.contextProperty("navigationBridge") if ctx else None
    assert nav is not None

    for r in NAV_ROUTES:
        nav.navigate(r)
        QCoreApplication.processEvents()
        cur = getattr(nav, 'currentRoute', None)
        assert cur is not None

    QCoreApplication.processEvents()
    QCoreApplication.processEvents()

    bootstrap.shutdown()
    assert bootstrap.container.state == ContainerState.STOPPED
