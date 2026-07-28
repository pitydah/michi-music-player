"""Replicate full user navigation sequence through all major routes.

D6 of the route reintegration plan.

Reproduces the recorded sidebar navigation workflow end to end: starting at
Inicio and walking through every major sidebar destination in order. Each step
verifies the navigation contract held by the real ``NavigationBridge`` +
``PageStack`` pair:

  1. ``navigationBridge.currentRoute == expectedRoute`` — the bridge accepted
     the destination and did not silently reject it.
  2. ``pageStack.currentPage != None`` — the PageStack instantiated a page for
     the route (no blank surface).
  3. ``pageStack.loadedObjectName`` matches the route's expected page root
     objectName — the CORRECT page loaded, not a generic placeholder.

The expected objectNames are taken from each page's source (the
``objectName:`` stamped on the page root). They are checked exactly because
the page objectNames in this codebase do not literally start with the dotted
route key (e.g. ``library.songs`` → ``tracksPage``, ``library.albums`` →
``albumGridPage``); an exact match is the strongest signal that the right page
rendered.

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

# The recorded sidebar navigation sequence: Inicio → library sub-routes →
# streaming → playlists → connections → audio_lab → home_audio → michi_ai →
# sync. Paired with each route's expected page-root objectName (taken from the
# page source).
NAV_SEQUENCE: list[tuple[str, str]] = [
    ("home", "homePage"),
    ("library.songs", "tracksPage"),
    ("library.albums", "albumGridPage"),
    ("library.artists", "artistGridPage"),
    ("library.genres", "genresPage"),
    ("library.composers", "composersPage"),
    ("library.folders", "folderBrowserPage"),
    ("streaming.radio", "radioPage"),
    ("playlists", "playlistsPage_control"),
    ("connections.micro_server", "connectionDiscoveryPage"),
    ("audio_lab.processing", "audioProcessingHubPage"),
    ("home_audio.stream", "homeAudioPage"),
    ("michi_ai", "assistantPage"),
    ("sync.mobile", "mobilePairingPage"),
]


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
    # Reset capability gating so every route in the sequence is navigable
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

def test_e2e_sidebar_navigation_sequence(runtime: _Runtime) -> None:
    """Walk the recorded sidebar navigation sequence end to end.

    Drives the real NavigationBridge + PageStack through every major sidebar
    destination in order, collecting failures per step so the full sequence is
    reported in one shot. Each step must satisfy the navigation contract:
    bridge accepted the route, PageStack instantiated a page, and the CORRECT
    page (by objectName) rendered.
    """
    nav = runtime.navigation
    page_stack = runtime.page_stack

    failures: list[str] = []

    for route, expected_name in NAV_SEQUENCE:
        nav.navigate(route)

        # 1. The bridge accepted the destination.
        if nav.currentRoute != route:
            failures.append(
                f"step {route!r}: navigationBridge.currentRoute="
                f"{nav.currentRoute!r} (expected {route!r})"
            )
            # Without the route accepted, the PageStack checks below are
            # meaningless — skip to the next step.
            continue

        # 2 + 3. The PageStack instantiated the CORRECT page for the route.
        settled = _wait_for_page(page_stack, route)
        if not settled:
            failures.append(
                f"step {route!r}: PageStack did not settle with a current page "
                f"(pageStack.currentRoute={page_stack.property('currentRoute')!r})"
            )
            continue

        current_page = page_stack.property("currentPage")
        if current_page is None:
            failures.append(
                f"step {route!r}: pageStack.currentPage is None — blank surface"
            )
            continue

        loaded_name = page_stack.property("loadedObjectName")
        if loaded_name != expected_name:
            failures.append(
                f"step {route!r}: wrong page rendered — objectName="
                f"{loaded_name!r} (expected {expected_name!r})"
            )

    assert not failures, (
        "E2E sidebar navigation sequence had failures:\n" + "\n".join(failures)
    )


@pytest.mark.parametrize(
    ("route", "expected_name"),
    [pytest.param(r, n, id=r) for r, n in NAV_SEQUENCE],
)
def test_each_route_loads_isolated(
    runtime: _Runtime, route: str, expected_name: str
) -> None:
    """Each route in the sequence loads correctly when navigated to from home.

    Companion to the sequence test: isolates each destination by navigating
    ``home → route`` so a single step failing does not mask the rest, and
    parametrizes for granular JUnit evidence.
    """
    nav = runtime.navigation
    page_stack = runtime.page_stack

    nav.navigate("home")
    _wait_for_page(page_stack, "home")

    nav.navigate(route)
    assert nav.currentRoute == route, (
        f"navigation to {route!r} failed: currentRoute={nav.currentRoute!r}"
    )

    settled = _wait_for_page(page_stack, route)
    assert settled, (
        f"PageStack did not settle on {route!r} "
        f"(pageStack.currentRoute={page_stack.property('currentRoute')!r})"
    )

    current_page = page_stack.property("currentPage")
    assert current_page is not None, f"pageStack.currentPage is None for {route!r}"

    loaded_name = page_stack.property("loadedObjectName")
    assert loaded_name == expected_name, (
        f"wrong page rendered for {route!r}: objectName={loaded_name!r} "
        f"(expected {expected_name!r})"
    )
