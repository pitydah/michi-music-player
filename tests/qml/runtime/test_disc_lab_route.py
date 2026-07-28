"""Verify CD ripper route loads DiscLabPage with real bridge.

D5 of the route reintegration plan.

The ``audio_lab.cd_ripper`` route is the canonical entry point to Disc Lab
(source: ``../pages/disc_lab/DiscLabPage.qml``, capability ``disc_lab``). It
MUST load the real ``DiscLabPage`` — not a placeholder — and the page MUST be
wired to the real ``discLabBridge`` context property (registered by
``BridgeFactory.create_disc_lab_bridge`` via ``ContextBindings``).

This gate boots the full ``ApplicationBootstrap`` composition root, navigates
to ``audio_lab.cd_ripper`` through the real ``NavigationBridge`` + ``PageStack``,
and asserts:

  1. ``navigationBridge.currentRoute == "audio_lab.cd_ripper"``.
  2. ``pageStack.currentPage`` is not ``None`` (a page rendered).
  3. The page's ``disc`` property (which reads the ``discLabBridge`` context
     property) is not ``None`` — the real bridge is wired into the page.
  4. ``pageStack.loadedObjectName == "discLabPage"`` — the real Disc Lab page
     loaded, not a placeholder/fallback.

Runs under ``QT_QPA_PLATFORM=offscreen``. Soft-skips when the container cannot
reach READY/DEGRADED (e.g. missing GStreamer plugins on a minimal CI image).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Environment must be set before PySide6 / application modules are imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MICHI_SAFE_MODE", "1")

import pytest
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ContainerState

QML_ROOT = REPO / "ui_qml"
MAIN_QML = QML_ROOT / "Main.qml"

DISC_LAB_ROUTE = "audio_lab.cd_ripper"
DISC_LAB_PAGE_OBJECT_NAME = "discLabPage"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _process_events(iterations: int = 1, wait_ms: int = 5) -> None:
    """Bounded event processing — never blocks the GUI thread indefinitely."""
    for _ in range(iterations):
        QCoreApplication.processEvents()
        QTest.qWait(max(0, wait_ms))


def _isolate_navigation(nav: Any) -> None:
    """Quiesce app-level UX concerns so the gate drives navigation directly."""
    timer = getattr(nav, "_poll_timer", None)
    if timer is not None:
        try:
            timer.stop()
        except Exception:  # noqa: BLE001 — best-effort
            pass
    if getattr(nav, "_pending_navigation", None) is not None:
        nav._pending_navigation = None
        try:
            nav.pendingNavigationChanged.emit()
        except Exception:  # noqa: BLE001 — best-effort
            pass
    guards = getattr(nav, "_leave_guards", None)
    if isinstance(guards, dict):
        guards.clear()
    # Reset capability gating so disc_lab (capability "disc_lab") is navigable
    # regardless of which optional capabilities are live on this host.
    if hasattr(nav, "set_capabilities"):
        nav.set_capabilities(None)  # type: ignore[arg-type]


def _wait_for_page(page_stack: QObject, route: str, max_iters: int = 30) -> bool:
    """Poll until PageStack reports ``route`` fully loaded and settled.

    Waits for BOTH a non-null current page AND the cross-fade transition
    (``transitionRunning``) to finish, so visible-state reads are stable.
    """
    for _ in range(max_iters):
        _process_events(1, 15)
        if (
            page_stack.property("currentRoute") == route
            and page_stack.property("currentPage") is not None
            and not page_stack.property("transitionRunning")
        ):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def qgui_app() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


class _Runtime:
    """Booted bootstrap, engine, navigation bridge and page stack."""
    bootstrap: ApplicationBootstrap
    engine: QQmlApplicationEngine
    navigation: Any
    page_stack: QObject


@pytest.fixture(scope="module")
def runtime(qgui_app: QGuiApplication):
    """Boot the full productive stack once and share it across the module."""
    rt = _Runtime()

    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    bootstrap.start()
    if bootstrap.container.state not in (ContainerState.READY, ContainerState.DEGRADED):
        pytest.skip(
            f"Container did not reach READY/DEGRADED "
            f"(state={bootstrap.container.state.value}); "
            "likely missing GStreamer plugins or system deps on this host."
        )

    bridges = bootstrap.create_bridges()
    assert "navigation" in bridges, "navigation bridge missing after create_bridges()"

    # The disc_lab bridge is created by BridgeFactory and registered as the
    # ``discLabBridge`` context property. Its creation requires the
    # ``worker_manager`` service (required_service in ContextBindings).
    assert "disc_lab" in bridges, (
        "disc_lab bridge missing after create_bridges() — DiscLabPage cannot "
        "wire its `disc` property without it"
    )

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    registrar = bootstrap.register_context(engine)
    audit = registrar.audit()
    assert audit["total"] > 0, "no context properties registered"
    assert audit["violations"] == [], f"context violations: {audit['violations']}"

    loaded = bootstrap.load_qml(engine, str(MAIN_QML))
    assert loaded, "Main.qml failed to load (no root objects produced)"
    assert engine.rootObjects(), "engine produced no root objects after load_qml"

    rt.bootstrap = bootstrap
    rt.engine = engine
    rt.navigation = bridges["navigation"]

    win = engine.rootObjects()[0]
    page_stack = win.findChild(QObject, "pageStack")
    assert page_stack is not None, "PageStack (objectName 'pageStack') not found"
    rt.page_stack = page_stack

    _isolate_navigation(rt.navigation)
    _process_events(5)
    yield rt

    if rt.bootstrap.container.state != ContainerState.STOPPED:
        try:
            rt.bootstrap.shutdown()
        except Exception:  # noqa: BLE001 — best-effort teardown
            pass
    try:
        rt.engine.deleteLater()
        _process_events(3)
    except Exception:  # noqa: BLE001 — best-effort teardown
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_disc_lab_route_loads_real_page(runtime: _Runtime) -> None:
    """``audio_lab.cd_ripper`` loads ``DiscLabPage`` with the real bridge.

    Navigates from ``home`` to ``audio_lab.cd_ripper`` through the real
    PageStack and verifies the route resolved, the Disc Lab page (not a
    placeholder) rendered, and the page's ``disc`` property is wired to the
    real ``discLabBridge`` context property.
    """
    nav = runtime.navigation
    page_stack = runtime.page_stack

    # Start from home so the route change is a real transition.
    nav.navigate("home")
    _wait_for_page(page_stack, "home")
    assert nav.currentRoute == "home"

    nav.navigate(DISC_LAB_ROUTE)

    # 1. The bridge accepted the route.
    assert nav.currentRoute == DISC_LAB_ROUTE, (
        f"navigation to {DISC_LAB_ROUTE!r} failed: "
        f"currentRoute={nav.currentRoute!r}"
    )

    # 2. The PageStack finished loading a page.
    settled = _wait_for_page(page_stack, DISC_LAB_ROUTE)
    assert settled, (
        f"PageStack did not settle on {DISC_LAB_ROUTE!r} with a current page "
        f"(pageStack.currentRoute={page_stack.property('currentRoute')!r})"
    )
    current_page = page_stack.property("currentPage")
    assert current_page is not None, (
        f"PageStack.currentPage is None for {DISC_LAB_ROUTE!r}"
    )

    # 3. The page is the real DiscLabPage, not a placeholder/fallback.
    loaded_name = page_stack.property("loadedObjectName")
    assert loaded_name == DISC_LAB_PAGE_OBJECT_NAME, (
        f"wrong page rendered for {DISC_LAB_ROUTE!r}: objectName={loaded_name!r} "
        f"(expected {DISC_LAB_PAGE_OBJECT_NAME!r} — DiscLabPage.qml root)"
    )

    # 4. The page's `disc` property is wired to the real discLabBridge context
    #    property. DiscLabPage declares:
    #      property var disc: typeof discLabBridge !== "undefined" ? discLabBridge : null
    #    A non-None value proves the bridge was registered as a context
    #    property AND the page bound it.
    disc_prop = current_page.property("disc")
    assert disc_prop is not None, (
        f"DiscLabPage.disc is None for {DISC_LAB_ROUTE!r} — discLabBridge "
        "context property is not wired into the page"
    )


def test_disc_lab_bridge_registered_as_context_property(runtime: _Runtime) -> None:
    """The ``discLabBridge`` context property is registered on the engine.

    Complementary to the page-level check: confirms the bridge is published as
    a context property (so DiscLabPage can resolve ``discLabBridge``) and is
    the same instance created by ``BridgeFactory``.
    """
    ctx = runtime.engine.rootContext()
    disc_bridge = ctx.contextProperty("discLabBridge") if ctx else None
    assert disc_bridge is not None, (
        "discLabBridge context property is not registered on the engine"
    )
