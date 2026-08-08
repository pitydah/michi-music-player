"""Productive runtime gate: boot Michi with real bridges, navigate routes.

This is the definitive QML runtime gate. Unlike ``QQmlComponent`` parsing
tests, it boots the full ``ApplicationBootstrap`` composition root, creates
every bridge through ``BridgeFactory(container).create_all()``, registers
real context properties on a ``QQmlApplicationEngine``, loads ``Main.qml``
and drives the real ``PageStack`` across the functional route matrix.

Verifies:
  1. The full service graph reaches READY/DEGRADED.
  2. ``Main.qml`` produces a root Window with a populated AppShell subtree.
  3. Every functional route is accepted by ``NavigationBridge`` and resolves
     to the expected ``currentRoute`` with no ``invalidRouteError``; every
     non-parametric functional route also loads through the real PageStack
     without ``Loader.Error`` (parametric detail routes are exercised for
     navigation only — dummy params may legitimately not instantiate).
  4. ``ZoneDetailPage`` exposes its declared QML signals at runtime and
     ``routeEnter`` applies the navigation params (``zoneId``) without error.
  5. ``bootstrap.shutdown()`` leaves the container ``STOPPED``.

Runs under ``QT_QPA_PLATFORM=offscreen``. Soft-skips when the container
cannot reach READY/DEGRADED (e.g. missing GStreamer plugins on a minimal CI
image). All event processing is bounded — no ``time.sleep`` on the GUI
thread, no unbounded waits.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Environment must be set before PySide6 / application modules are imported.
# QT_QPA_PLATFORM=offscreen keeps the gate headless; MICHI_SAFE_MODE=1 keeps
# optional/audio-dependent features quiet so the gate can run on minimal hosts.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MICHI_SAFE_MODE", "1")

import pytest
from PySide6.QtCore import (
    QCoreApplication,
    QMetaMethod,
    QObject,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtTest import QTest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ContainerState
from ui_qml_bridge.bridge_factory import BridgeFactory  # noqa: F401  — exercised via bootstrap.create_bridges()
from ui_qml_bridge.route_registry import ROUTES

QML_ROOT = REPO / "ui_qml"
MAIN_QML = QML_ROOT / "Main.qml"

# Signals declared in ui_qml/pages/home_audio/ZoneDetailPage.qml.
# Verified at runtime via QMetaObject introspection (not source parsing).
ZONE_DETAIL_SIGNALS = {
    "backClicked",
    "deleteRequested",
    "groupClicked",
    "muteToggled",
    "reconnectClicked",
    "renameRequested",
    "sourceChanged",
    "ungroupClicked",
    "zoneDetailVolumeChanged",
}

# A tiny QML wrapper that loads ZoneDetailPage.qml with the real bridges and
# invokes routeEnter from QML. PySide6's QMetaObject.invokeMethod cannot pass
# Python arguments to a QML function, so we drive routeEnter from a Loader's
# onLoaded handler — this is the same call site the real PageStack uses.
# The base URL is set to ui_qml/ so the relative `source` resolves correctly.
_ZONE_DETAIL_PROBE_QML = """import QtQuick
Item {
    objectName: "zone_detail_probe"
    Loader {
        id: pageLoader
        source: "pages/home_audio/ZoneDetailPage.qml"
        onLoaded: {
            if (item && typeof item.routeEnter === "function") {
                item.routeEnter("zone_detail", {"zone_id": "zone-1"})
            }
        }
    }
    property var probedItem: pageLoader.item
    property string probedZoneId: pageLoader.item ? pageLoader.item.zoneId : ""
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _process_events(iterations: int = 1, wait_ms: int = 5) -> None:
    """Bounded event processing — never blocks the GUI thread indefinitely."""
    for _ in range(iterations):
        QCoreApplication.processEvents()
        QTest.qWait(max(0, wait_ms))


def _wait_for_qml_incubation(
    engine: QQmlApplicationEngine, max_iterations: int = 100
) -> bool:
    """Process events until all asynchronous QML object creation is terminal."""
    controller = engine.incubationController()
    if controller is None:
        _process_events(1)
        return True
    stable_iterations = 0
    for _ in range(max_iterations):
        _process_events(1)
        if controller.incubatingObjectCount() == 0:
            stable_iterations += 1
            if stable_iterations == 3:
                return True
        else:
            stable_iterations = 0
    return False


def _count_descendants(obj: QObject, max_depth: int = 6) -> int:
    """Count descendants of ``obj`` up to ``max_depth`` as an AppShell proxy."""
    count = 0

    def walk(node: QObject, depth: int) -> None:
        nonlocal count
        if depth > max_depth:
            return
        count += 1
        for child in node.children():
            walk(child, depth + 1)

    walk(obj, 0)
    return count


def _functional_routes() -> list[tuple[str, dict]]:
    """Return ``[(route_key, spec), ...]`` for every functional route."""
    return [
        (key, spec)
        for key, spec in ROUTES.items()
        if spec.get("status") == "functional"
    ]


def _dummy_params(spec: dict) -> dict:
    """Build valid dummy params for a route's required param spec.

    ``NavigationBridge._validate_params`` rejects navigations to param routes
    when a required param is missing, so we always supply one of the right
    primitive type.
    """
    params_spec = spec.get("params")
    if not isinstance(params_spec, dict):
        return {}
    params: dict[str, Any] = {}
    for key, pspec in params_spec.items():
        if not isinstance(pspec, dict):
            params[key] = "dummy"
            continue
        ptype = pspec.get("type", "string")
        if ptype == "int":
            params[key] = 1
        elif ptype == "object":
            params[key] = {"id": "dummy"}
        else:
            params[key] = "dummy"
    return params


def _source_filename(spec: dict) -> str:
    source = spec.get("source", "")
    return Path(source).name if source else ""


def _isolate_navigation(nav: Any) -> None:
    """Quiesce app-level UX concerns so the matrix drives navigation directly.

    Three things make a synchronous route matrix non-deterministic, and all
    are app-level behaviours unrelated to the route-loading contract under
    test:

      * The bridge's 100ms poll timer re-injects navigation requests from
        ``NavigationService`` (e.g. deep links queued during boot).
      * The settings leave guard blocks navigation when the bridge lands on
        a ``settings`` route with pending changes.
      * ``CapabilityBridge.refresh()`` (run at the end of ``create_all``)
        populates host capabilities, which gates routes whose prefix
        requires a capability not available on this host (e.g. ``connections``,
        ``audio_lab.*``, ``sync.*``).

    We stop the timer, clear guards/pending state and reset capability
    gating so every functional route is navigable for the duration of the
    matrix.
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
    # Reset capability gating so the matrix covers every functional route
    # regardless of which optional capabilities are live on this host.
    if hasattr(nav, "set_capabilities"):
        nav.set_capabilities(None)  # type: ignore[arg-type]


class _MessageCapture:
    """Context manager that captures Qt messages for the duration of a block.

    Messages are swallowed (not printed) to keep test output clean; callers
    inspect ``route_load_errors_since`` to detect ``PageStack`` load failures.
    """

    def __init__(self, engine: QQmlApplicationEngine) -> None:
        self._engine = engine
        self.messages: list[tuple[int, str]] = []
        self.qml_warnings: list[str] = []
        self._prev: Any = None

    def __enter__(self) -> "_MessageCapture":
        self._prev = qInstallMessageHandler(self._handler)
        self._engine.warnings.connect(self._on_qml_warnings)
        return self

    def __exit__(self, *exc: object) -> bool:
        self._engine.warnings.disconnect(self._on_qml_warnings)
        qInstallMessageHandler(self._prev)
        return False

    def _handler(self, msg_type: QtMsgType, context: Any, message: str) -> None:
        self.messages.append((int(msg_type), message))

    def _on_qml_warnings(self, warnings: list[Any]) -> None:
        self.qml_warnings.extend(error.toString() for error in warnings)

    def route_load_errors_since(self, start: int, source_filename: str) -> list[str]:
        """Return critical messages that look like a PageStack route failure."""
        out: list[str] = []
        for lvl, msg in self.messages[start:]:
            if lvl < int(QtMsgType.QtCriticalMsg):
                continue
            if (
                "Route load error" in msg
                or "PageStack" in msg
                or "Cannot create" in msg
                or (bool(source_filename) and source_filename in msg)
            ):
                out.append(msg)
        return out


def _meta_signal_names(obj: QObject) -> set[str]:
    """Return the set of QML-declared signal names on ``obj`` at runtime."""
    meta = obj.metaObject()
    names: set[str] = set()
    for i in range(meta.methodCount()):
        method = meta.method(i)
        if method.methodType() != QMetaMethod.Signal:
            continue
        # PySide6 returns a QByteArray; bytes() yields the raw bytes.
        names.add(bytes(method.name()).decode("utf-8"))
    return names


def _load_zone_detail_probe(
    bootstrap: ApplicationBootstrap,
) -> tuple[QObject, QQmlApplicationEngine, QQmlComponent] | None:
    """Create a deterministic ZoneDetailPage probe on an isolated engine.

    The probe loads ZoneDetailPage.qml via a Loader and calls ``routeEnter``
    from QML on load. An isolated engine avoids lifetime interference from the
    main app's AppShell/PageStack. Real bridges are registered via the same
    ``ContextRegistrar`` used at boot. Returns ``(probe_obj, engine, component)``
    — all three must be kept alive by the caller (PySide6 parents the created
    object to the component, so the component must outlive the probe) — or
    ``None`` if the probe component did not reach Ready state.
    """
    from PySide6.QtQml import QQmlEngine

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    bootstrap.register_context(engine)

    component = QQmlComponent(engine)
    component.setData(
        _ZONE_DETAIL_PROBE_QML.encode("utf-8"),
        QUrl.fromLocalFile(str(QML_ROOT / "probe.qml")),
    )
    if component.status() != QQmlComponent.Ready:
        engine.deleteLater()
        _process_events(1)
        return None
    obj = component.create()
    if obj is None:
        engine.deleteLater()
        _process_events(1)
        return None
    # QQmlComponent.create() grants JavaScript ownership, so the QML GC could
    # collect the probe during event processing even though Python holds a
    # reference. Force C++ ownership so the probe lives until we delete it.
    QQmlEngine.setObjectOwnership(obj, QQmlEngine.CppOwnership)
    return obj, engine, component


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
    """Booted bootstrap, engine and navigation bridge shared across tests."""

    bootstrap: ApplicationBootstrap
    engine: QQmlApplicationEngine
    navigation: Any
    bridges: dict[str, QObject]


@pytest.fixture(scope="module")
def runtime(qgui_app: QGuiApplication):
    """Boot the full productive stack once and share it across the module."""
    rt = _Runtime()

    # 1. Build the full composition root.
    bootstrap = ApplicationBootstrap()
    bootstrap.build()

    # 2. Start services — soft-skip if REQUIRED services fail (e.g. GStreamer
    #    plugins missing on a minimal CI image).
    bootstrap.start()
    if bootstrap.container.state not in (ContainerState.READY, ContainerState.DEGRADED):
        pytest.skip(
            f"Container did not reach READY/DEGRADED "
            f"(state={bootstrap.container.state.value}); "
            "likely missing GStreamer plugins or system deps on this host."
        )

    # 3. Create bridges via BridgeFactory(container).create_all().
    #    bootstrap.create_bridges() delegates to exactly that call and also
    #    publishes the result so register_context() can wire them.
    bridges = bootstrap.create_bridges()
    assert "navigation" in bridges, "navigation bridge missing after create_bridges()"
    assert "theme" in bridges, "theme bridge missing after create_bridges()"
    assert "app" in bridges, "app bridge missing after create_bridges()"

    # 4. Boot the QML engine and register real context properties.
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))
    registrar = bootstrap.register_context(engine)
    audit = registrar.audit()
    assert audit["total"] > 0, "no context properties registered"
    assert audit["violations"] == [], f"context violations: {audit['violations']}"

    # 5. Load Main.qml.
    loaded = bootstrap.load_qml(engine, str(MAIN_QML))
    assert loaded, "Main.qml failed to load (no root objects produced)"
    assert engine.rootObjects(), "engine produced no root objects after load_qml"

    rt.bootstrap = bootstrap
    rt.engine = engine
    rt.navigation = bridges["navigation"]
    rt.bridges = bridges

    # Let AppShell / PageStack settle before tests drive navigation.
    _process_events(5)
    yield rt

    # 7. Shutdown cleanly (also defensive if test_clean_shutdown was skipped).
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

def test_productive_boot_smoke(runtime: _Runtime) -> None:
    """Main.qml loaded and instantiated a populated AppShell subtree."""
    roots = runtime.engine.rootObjects()
    assert roots, "Main.qml produced no root objects"
    win = roots[0]
    descendants = _count_descendants(win, max_depth=6)
    assert descendants > 10, (
        f"AppShell subtree too small ({descendants} nodes) — "
        "AppShell likely not instantiated"
    )


def test_navigate_functional_route_matrix(runtime: _Runtime) -> None:
    """Navigate every functional route with real context properties."""
    nav = runtime.navigation
    _isolate_navigation(nav)

    routes = _functional_routes()
    assert routes, "no functional routes found in route_registry"

    failures: list[str] = []
    with _MessageCapture(runtime.engine) as capture:
        for route_key, spec in routes:
            params = _dummy_params(spec)
            source_file = _source_filename(spec)
            before = len(capture.messages)
            warnings_before = len(capture.qml_warnings)

            try:
                if params:
                    nav.navigateWithParams(route_key, params)
                else:
                    nav.navigate(route_key)
            except Exception as exc:  # noqa: BLE001 — collect, don't abort
                failures.append(
                    f"route '{route_key}': navigation raised {exc!r}"
                )
                continue

            # currentRoute is a Qt Property — read synchronously, before any
            # event processing that could let the PageStack react.
            current = nav.currentRoute
            if current != route_key:
                failures.append(
                    f"route '{route_key}': currentRoute={current!r} "
                    f"(expected {route_key!r})"
                )
                continue

            incubation_settled = _wait_for_qml_incubation(runtime.engine)

            # PageStack load errors are only asserted for non-parametric
            # routes — detail routes use dummy params that may legitimately
            # not instantiate (their navigation contract is still verified
            # above by the currentRoute assertion).
            if not params:
                if not incubation_settled:
                    failures.append(
                        f"route '{route_key}' ({source_file}): "
                        "QML object still incubating before next navigation"
                    )
                load_errors = capture.route_load_errors_since(before, source_file)
                if load_errors:
                    qml_warnings = capture.qml_warnings[warnings_before:]
                    failures.append(
                        f"route '{route_key}' ({source_file}): "
                        f"PageStack load errors: {load_errors}; "
                        f"QML component warnings: {qml_warnings}"
                    )

    assert not failures, (
        "Functional route matrix had failures:\n" + "\n".join(failures)
    )


@pytest.mark.qml_route("zone_detail")
def test_zone_detail_signals_and_route_enter(runtime: _Runtime) -> None:
    """ZoneDetailPage exposes its signals and routeEnter applies params.

    Two complementary checks:
      * App-level: navigate to ``zone_detail`` via the real PageStack and
        confirm ``currentRoute`` resolves with no PageStack load errors.
      * Component probe: instantiate ZoneDetailPage with the real bridges on
        an isolated engine and invoke ``routeEnter`` from QML (the same call
        site PageStack uses), then verify the declared signals exist on the
        runtime meta-object and that ``zoneId`` was populated from params.
    """
    nav = runtime.navigation
    _isolate_navigation(nav)

    # ── App-level navigation through the real PageStack ──────────────────────
    with _MessageCapture(runtime.engine) as capture:
        before = len(capture.messages)
        # Navigate away first so zone_detail is a route *change* (routeEnter
        # only fires on change, not on param-only updates).
        nav.navigate("home")
        _process_events(3, wait_ms=5)
        nav.navigateWithParams("zone_detail", {"zone_id": "zone-1"})
        _process_events(6, wait_ms=25)

        assert nav.currentRoute == "zone_detail", (
            f"navigation to zone_detail failed: "
            f"currentRoute={nav.currentRoute!r}"
        )
        app_errors = capture.route_load_errors_since(before, "ZoneDetailPage.qml")
        assert not app_errors, (
            f"PageStack load errors for zone_detail: {app_errors}"
        )

    # ── Deterministic component probe on an isolated engine ──────────────────
    probe_pair = _load_zone_detail_probe(runtime.bootstrap)
    assert probe_pair is not None, (
        "zone_detail probe component did not reach Ready state"
    )
    probe, probe_engine, probe_component = probe_pair
    try:
        # Let the Loader instantiate ZoneDetailPage and fire onLoaded.
        for _ in range(10):
            _process_events(1, wait_ms=15)
            if probe.property("probedItem") is not None:
                break

        probed_item = probe.property("probedItem")
        assert probed_item is not None, (
            "probe Loader did not yield a ZoneDetailPage instance"
        )

        # routeEnter sets root.zoneId from params.zoneId before doing anything
        # else — a populated zoneId proves routeEnter ran without throwing.
        probed_zone_id = probe.property("probedZoneId")
        assert probed_zone_id == "zone-1", (
            f"routeEnter did not apply zone_id param: "
            f"probedZoneId={probed_zone_id!r}"
        )

        # Declared QML signals must be present on the runtime meta-object.
        signals = _meta_signal_names(probed_item)
        missing = ZONE_DETAIL_SIGNALS - signals
        assert not missing, (
            f"ZoneDetailPage missing declared signals: {sorted(missing)} "
            f"(found: {sorted(signals & ZONE_DETAIL_SIGNALS)})"
        )
    finally:
        try:
            probe_engine.deleteLater()
            _process_events(2)
        except Exception:  # noqa: BLE001 — best-effort teardown
            pass


def test_clean_shutdown(runtime: _Runtime) -> None:
    """bootstrap.shutdown() leaves the container STOPPED."""
    runtime.bootstrap.shutdown()
    assert runtime.bootstrap.container.state == ContainerState.STOPPED


# ─────────────────────────────────────────────────────────────────────────────
# Reusable productive boot
# ─────────────────────────────────────────────────────────────────────────────


def build_and_boot() -> _Runtime:
    """Boot the full productive stack and return a runtime handle.

    This is the fixture-free form of the ``runtime`` module fixture: it
    builds the composition root, starts services, creates every bridge
    through ``BridgeFactory(container).create_all()``, registers the real
    context properties on a ``QQmlApplicationEngine`` and loads
    ``Main.qml``. Intended for test modules that want their own one-shot
    productive boot (e.g. the sidebar route matrix) without depending on
    the module-scoped ``runtime`` fixture.

    Soft-skips via ``pytest.skip`` when the container cannot reach
    READY/DEGRADED (e.g. missing GStreamer plugins on a minimal CI image).
    The caller owns the returned runtime and should shut down its
    ``bootstrap`` (or rely on process-exit teardown).
    """
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)

    rt = _Runtime()

    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    bootstrap.start()
    if bootstrap.container.state not in (ContainerState.READY, ContainerState.DEGRADED):
        try:
            bootstrap.shutdown()
        except Exception:  # noqa: BLE001 — best-effort teardown
            pass
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
    rt.bridges = bridges

    _process_events(5)
    return rt
