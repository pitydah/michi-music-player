"""Verify routes load even when capability is unavailable — page shows degraded state.

D4 of the route reintegration plan.

The navigation contract is: a route's ``capability`` field is INFORMATIONAL
only. ``NavigationBridge.routeAvailability()`` reports ``unavailable`` when the
host lacks the required capability, but ``navigate()`` MUST still accept the
route and the ``PageStack`` MUST still render the route's source page (the real
page, or a planned/placeholder page for non-functional statuses) — never a
blank surface, and never silently keeping the previous page visible.

This gate boots the full ``ApplicationBootstrap`` composition root (real
bridges, real context properties, real ``Main.qml`` + ``PageStack``), sets a
LIMITED capability set (a non-empty set that excludes every real capability so
``routeAvailability()`` genuinely reports ``unavailable`` for capability-gated
routes), then navigates to each capability-gated route and asserts:

  1. ``navigationBridge.currentRoute == route`` — the route was accepted, not
     blocked, even though ``routeAvailability().state == "unavailable"``.
  2. ``pageStack.currentPage`` is not ``None`` — a page rendered (the route's
     real source or its planned/placeholder page), not a blank surface.
  3. ``pageStack.loadedObjectName`` matches the route's expected page — the
     correct page rendered, not a generic fallback.
  4. ``pageStack.previousRoute == "home"`` and the transition finished — the
     previous page (home) was swapped out and is no longer the visible page.

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
from ui_qml_bridge.route_registry import ROUTES

QML_ROOT = REPO / "ui_qml"
MAIN_QML = QML_ROOT / "Main.qml"

# Routes that carry a capability requirement (or sit under a capability-gated
# section) together with the objectName their source page stamps on its root.
# The capability column is read live from ``ROUTES`` so the test tracks the
# registry, but the pairings are documented here for clarity:
#   connections.navidrome  → capability "navidrome"  (status: planned)
#   audio_lab.processing   → capability "audio_lab"  (status: functional)
#   home_audio.rooms       → capability "home_audio" (status: partial)
#   sync.mobile            → capability "sync"        (status: functional)
#   settings.appearance    → no capability            (status: functional)
CAPABILITY_ROUTES: list[tuple[str, str]] = [
    ("connections.navidrome", "navidromePage"),
    ("audio_lab.processing", "audioProcessingHubPage"),
    ("home_audio.rooms", "roomsHubPage"),
    ("sync.mobile", "mobilePairingPage"),
    ("settings.appearance", "settingsAppearancePage"),
]

# A non-empty capability set that excludes every real capability key. With this
# set installed, ``NavigationBridge.routeAvailability()`` reports ``unavailable``
# for any route whose ``capability`` field is set — exercising the exact path
# the gate must prove non-blocking.
LIMITED_CAPABILITIES: set[str] = {"__unrelated__"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _process_events(iterations: int = 1, wait_ms: int = 5) -> None:
    """Bounded event processing — never blocks the GUI thread indefinitely."""
    for _ in range(iterations):
        QCoreApplication.processEvents()
        QTest.qWait(max(0, wait_ms))


def _isolate_navigation(nav: Any) -> None:
    """Quiesce app-level UX concerns so the gate drives navigation directly.

    Stops the bridge's 100ms poll timer (re-injects deep links queued during
    boot), clears leave guards/pending state, and resets capability gating.
    The test re-installs a LIMITED capability set afterwards via
    ``set_capabilities`` to exercise the unavailable path.
    """
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


def _wait_for_page(page_stack: QObject, route: str, max_iters: int = 30) -> bool:
    """Poll until PageStack reports ``route`` fully loaded and settled.

    The PageStack uses asynchronous Loaders AND a 180ms cross-fade transition
    (``transitionRunning``) once the incoming loader reaches Ready. We must
    wait for BOTH the current page to be non-null AND the transition to finish
    before reading visible-state properties — otherwise ``transitionRunning``
    is still true and the previous page may still be the active loader.
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

    # Locate the real PageStack (objectName "pageStack") under the AppShell.
    win = engine.rootObjects()[0]
    page_stack = win.findChild(QObject, "pageStack")
    assert page_stack is not None, "PageStack (objectName 'pageStack') not found"
    rt.page_stack = page_stack

    _isolate_navigation(rt.navigation)
    # Let AppShell / PageStack settle before tests drive navigation.
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

@pytest.mark.parametrize(
    ("route", "expected_object_name"),
    [pytest.param(r, n, id=r) for r, n in CAPABILITY_ROUTES],
)
def test_capability_does_not_block_route(
    runtime: _Runtime, route: str, expected_object_name: str
) -> None:
    """A route loads and renders even when its capability is unavailable.

    Installs a limited capability set that excludes the route's required
    capability (so ``routeAvailability()`` reports ``unavailable``), navigates
    from ``home`` to the route, and asserts the route was accepted, a real page
    rendered, and the previous (home) page is no longer the visible page.
    """
    nav = runtime.navigation
    page_stack = runtime.page_stack

    # Install the limited capability set. For routes WITH a capability this
    # makes routeAvailability() report "unavailable"; for settings.appearance
    # (no capability) it stays "available". Either way navigation must succeed.
    nav.set_capabilities(LIMITED_CAPABILITIES)

    spec = ROUTES.get(route, {})
    cap = spec.get("capability")
    availability = nav.routeAvailability(route)
    if cap:
        # Document the precondition: the capability IS reported missing on
        # this host. This is the exact condition the gate proves non-blocking.
        assert availability.get("state") == "unavailable", (
            f"precondition failed for {route!r}: expected routeAvailability "
            f"state 'unavailable' for capability {cap!r}, got {availability!r}"
        )
    else:
        assert availability.get("state") == "available", (
            f"precondition failed for {route!r}: expected routeAvailability "
            f"state 'available' (no capability), got {availability!r}"
        )

    # Start from home so the previous page is deterministic.
    nav.navigate("home")
    _wait_for_page(page_stack, "home")
    assert nav.currentRoute == "home", (
        f"failed to reset to home before navigating to {route!r} "
        f"(currentRoute={nav.currentRoute!r})"
    )

    # Navigate to the capability-gated route — this MUST not be blocked.
    nav.navigate(route)

    # The bridge accepts the route synchronously.
    assert nav.currentRoute == route, (
        f"route {route!r} was NOT accepted (currentRoute={nav.currentRoute!r}); "
        "capability must not block navigation"
    )

    # The PageStack must finish loading the route's source page.
    settled = _wait_for_page(page_stack, route)
    assert settled, (
        f"PageStack did not settle on {route!r} with a current page "
        f"(pageStack.currentRoute={page_stack.property('currentRoute')!r})"
    )

    # A page rendered — not a blank surface.
    current_page = page_stack.property("currentPage")
    assert current_page is not None, (
        f"PageStack.currentPage is None for {route!r} — blank surface"
    )

    # The correct page rendered (the route's real source or its planned/
    # placeholder page), not a generic fallback.
    loaded_name = page_stack.property("loadedObjectName")
    assert loaded_name == expected_object_name, (
        f"wrong page rendered for {route!r}: objectName={loaded_name!r} "
        f"(expected {expected_object_name!r})"
    )

    # The previous page (home) is no longer the visible page: PageStack
    # advanced to the new route, the transition finished, and the previous
    # route is recorded as "home".
    assert page_stack.property("currentRoute") == route, (
        f"PageStack.currentRoute={page_stack.property('currentRoute')!r} "
        f"!= {route!r} — previous page still active"
    )
    assert page_stack.property("previousRoute") == "home", (
        f"PageStack.previousRoute={page_stack.property('previousRoute')!r} "
        f"!= 'home' — previous page was not swapped out for {route!r}"
    )
    assert not page_stack.property("transitionRunning"), (
        f"PageStack transition still running for {route!r} — previous page "
        "may still be visible"
    )


def test_limited_capabilities_do_not_persist_after_reset(runtime: _Runtime) -> None:
    """Resetting capabilities to ``None`` clears the unavailable state.

    Sanity check that the limited set installed by the parametrized test is
    reversible: after ``set_capabilities(None)``, routeAvailability() reports
    ``available`` for capability-gated routes again.
    """
    nav = runtime.navigation
    nav.set_capabilities(None)
    # audio_lab.processing has capability "audio_lab" — with caps reset, it
    # must report available.
    availability = nav.routeAvailability("audio_lab.processing")
    assert availability.get("state") == "available", (
        f"capability reset did not clear unavailable state: {availability!r}"
    )
