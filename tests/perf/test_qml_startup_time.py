"""Startup time benchmarks for QML bridge components."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.qml_module("perf"),
    pytest.mark.qml_dimension("performance"),
]

TARGET_MS = 500


def _delta_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def test_route_registry_load():
    t0 = time.perf_counter()
    from ui_qml_bridge.route_registry import ROUTES
    elapsed = _delta_ms(t0)
    assert elapsed < 500, f"route_registry load took {elapsed:.1f}ms"
    assert len(ROUTES) > 0


def test_navigation_bridge_instantiation(_qt_app):
    t0 = time.perf_counter()
    from ui_qml_bridge.navigation_bridge import NavigationBridge
    nav = NavigationBridge()
    elapsed = _delta_ms(t0)
    assert elapsed < 200, f"NavigationBridge init took {elapsed:.1f}ms"
    assert nav is not None


def test_bridge_factory_creation(_qt_app):
    from ui_qml_bridge.bridge_factory import BridgeFactory
    t0 = time.perf_counter()
    factory = BridgeFactory(MagicMock())
    elapsed = _delta_ms(t0)
    assert elapsed < 200, f"BridgeFactory init took {elapsed:.1f}ms"
    assert factory is not None


def test_context_registrar_creation(_qt_app):
    t0 = time.perf_counter()
    from ui_qml_bridge.context_registrar import ContextRegistrar
    registrar = ContextRegistrar(None)
    elapsed = _delta_ms(t0)
    assert elapsed < 100, f"ContextRegistrar init took {elapsed:.1f}ms"
    assert registrar is not None


def test_cover_bridge_import(_qt_app):
    t0 = time.perf_counter()
    from ui_qml_bridge.cover_bridge import CoverBridge
    elapsed = _delta_ms(t0)
    assert elapsed < 500, f"CoverBridge import took {elapsed:.1f}ms"
    assert CoverBridge is not None


def test_full_bridge_factory_phases(_qt_app):
    from ui_qml_bridge.bridge_factory import BridgeFactory
    factory = BridgeFactory(MagicMock())
    t0 = time.perf_counter()
    bridges = factory.create_all()
    elapsed = _delta_ms(t0)
    assert elapsed < 5000, f"BridgeFactory.create_all took {elapsed:.1f}ms"
    assert len(bridges) > 20
    assert "navigation" in bridges
    assert "home" in bridges


def test_library_query_service_init():
    from ui_qml_bridge.library_query_service import LibraryQueryService  # noqa: F401
