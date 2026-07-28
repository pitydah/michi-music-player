"""Rapid navigation: only the last request should load.

D3 of the QML route reintegration plan (P0-C0.5).

Proves the PageStack's generation-safe atomic route replacement: when
several ``loadRoute`` calls land back-to-back without event processing,
only the most recent request is honoured. Earlier requests are discarded
(stale ``source`` resets) so no intermediate page ever becomes visible.

The contract verified here is the one introduced in C4:
  * ``lastLoadedRoute`` ends up at the final requested route.
  * Exactly one managed ``Loader`` is visible and enabled.
  * The non-active loader has no ``source`` and no ``item`` — i.e. no
    visible object from any of the superseded routes survives.

Runs headless under ``QT_QPA_PLATFORM=offscreen``.
"""
from __future__ import annotations

import os
from pathlib import Path

# QT_QPA_PLATFORM must be set before PySide6 is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge

REPO = Path(__file__).resolve().parents[3]
QML_ROOT = REPO / "ui_qml"

# Four library sub-routes that share the same parent. Requested in rapid
# succession, the first three must be discarded and only "library.folders"
# (the last) must reach ``lastLoadedRoute``.
RAPID_SEQUENCE = (
    "library.artists",
    "library.genres",
    "library.composers",
    "library.folders",
)
FINAL_ROUTE = RAPID_SEQUENCE[-1]


def _unwrap(value):
    """Unwrap a QVariant-backed QML property value to its Python form."""
    if value is None:
        return None
    if hasattr(value, "toVariant"):
        return value.toVariant()
    return value


def _source_string(loader) -> str:
    """Return a Loader's ``source`` as a plain string ("" when empty)."""
    source = loader.property("source") if loader is not None else None
    if source is None:
        return ""
    if hasattr(source, "toString"):
        return source.toString()
    return str(source)


@pytest.fixture
def engine(qapp) -> QQmlEngine:
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    registry = RouteRegistryBridge()
    qml_engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    yield qml_engine
    qml_engine.deleteLater()


@pytest.fixture
def page_stack(engine) -> object:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "shell/PageStack.qml")))
    assert component.isReady(), component.errorString()
    stack = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert stack is not None, component.errorString()
    yield stack
    stack.deleteLater()


def _settle(stack, qapp) -> None:
    """Pump events until the current load finalizes its cross-fade."""
    for _ in range(300):
        qapp.processEvents()
        if (
            stack.property("lastLoadedRoute") == FINAL_ROUTE
            and not stack.property("transitionRunning")
        ):
            return
        QTest.qWait(10)


def test_rapid_navigation_keeps_only_last_request(page_stack, qapp) -> None:
    """Only the last of four rapid loadRoute calls reaches lastLoadedRoute."""
    stack = page_stack

    # Fire all four requests with no event processing in between. Each call
    # resets the incoming loader's source, so only the final source survives.
    for route in RAPID_SEQUENCE:
        stack.loadRoute(route)

    _settle(stack, qapp)

    # ── The last request wins ────────────────────────────────────────────
    assert stack.property("lastLoadedRoute") == FINAL_ROUTE
    assert stack.property("currentRoute") == FINAL_ROUTE
    assert stack.property("loading") is False
    assert stack.property("lastError") == ""
    assert stack.property("currentPage") is not None

    # ── Exactly one managed Loader is the visible page ───────────────────
    active = _unwrap(stack.property("_activeLoader"))
    incoming = _unwrap(stack.property("_incomingLoader"))
    assert active is not None, "_activeLoader is not exposed on the PageStack"
    assert incoming is not None, "_incomingLoader is not exposed on the PageStack"
    loaders = [active, incoming]

    visible_loaders = [loader for loader in loaders if loader.property("visible")]
    enabled_loaders = [loader for loader in loaders if loader.property("enabled")]
    assert len(visible_loaders) == 1, (
        f"expected exactly one visible loader, got {len(visible_loaders)}"
    )
    assert len(enabled_loaders) == 1, (
        f"expected exactly one enabled loader, got {len(enabled_loaders)}"
    )

    # ── The superseded loader holds no source and no item ────────────────
    # The active loader is the one that survived; the incoming loader is the
    # freed one (finalized by the cross-fade). The freed loader must carry
    # no source and no instantiated page — i.e. no visible object from any
    # of the three discarded routes (artists/genres/composers).
    assert _source_string(active) != "", "active loader lost its source"
    assert _source_string(incoming) == "", (
        f"superseded loader still has a source: {_source_string(incoming)!r}"
    )
    assert incoming.property("item") is None, (
        "superseded loader still holds an instantiated page"
    )
    assert incoming.property("visible") is False
    assert incoming.property("enabled") is False


def test_rapid_navigation_discards_stale_sources_only(page_stack, qapp) -> None:
    """The three discarded routes leave no instantiated objects behind.

    Independent of which loader is active/incoming, no managed loader may
    carry a source for any route other than the final one. This is the
    stale-discard guarantee: a superseded generation never renders.
    """
    stack = page_stack

    for route in RAPID_SEQUENCE:
        stack.loadRoute(route)

    _settle(stack, qapp)
    assert stack.property("lastLoadedRoute") == FINAL_ROUTE

    discarded = RAPID_SEQUENCE[:-1]
    active = _unwrap(stack.property("_activeLoader"))
    incoming = _unwrap(stack.property("_incomingLoader"))
    for loader in (active, incoming):
        source = _source_string(loader)
        for stale in discarded:
            stale_file = stale.split(".")[-1]
            assert stale_file not in source.lower(), (
                f"stale route {stale!r} survived in loader source {source!r}"
            )
