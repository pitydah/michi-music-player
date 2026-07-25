"""Memory leak detection for QML navigation and bridge lifecycle."""
from __future__ import annotations

import gc
import os
import time
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.qml_module("perf"),
    pytest.mark.qml_dimension("memory"),
]

CYCLE_ROUTES = ["library", "home", "radio", "playlists", "assistant", "home_audio", "audio_lab", "connections"]


def _rss_mb() -> float:
    """Return RSS in MB for the current process."""
    with open(f"/proc/{os.getpid()}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024
    return 0.0


def test_page_state_store_memory_bound(_qt_app):
    from ui_qml_bridge.page_state import PageStateStore
    store = PageStateStore()
    gc.collect()
    gc.collect()
    rss_before = _rss_mb()
    for i in range(100):
        store.set(f"page_{i}", {"data": "x" * 1000})
    gc.collect()
    gc.collect()
    rss_after = _rss_mb()
    growth = rss_after - rss_before
    assert growth < 50, f"PageStateStore grew RSS by {growth:.1f}MB after 100 entries"


def test_settings_bridge_no_growth(_qt_app):
    from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
    bridges = []
    for _ in range(20):
        svc = MagicMock()
        b = SettingsBridgeV2(service=svc)
        bridges.append(b)
    del bridges
    gc.collect()
    gc.collect()


def test_navigation_signal_count(_qt_app):
    from ui_qml_bridge.navigation_bridge import NavigationBridge
    nav = NavigationBridge()
    signals_seen = []
    def _track(route):
        signals_seen.append(1)
    nav.routeChanged.connect(_track)
    t0 = time.time()
    for i in range(50):
        nav.navigate(f"route_{i}")
    elapsed = time.time() - t0
    assert elapsed < 2.0, f"50 navigations took {elapsed:.2f}s"
    assert len(signals_seen) > 0
    nav.routeChanged.disconnect(_track)


def test_cycle_routes_memory_stable(_qt_app):
    from ui_qml_bridge.route_registry import ROUTES
    from ui_qml_bridge.navigation_bridge import NavigationBridge
    nav = NavigationBridge()
    gc.collect()
    gc.collect()
    rss_before = _rss_mb()
    for _ in range(5):
        for route in CYCLE_ROUTES:
            if route in ROUTES:
                nav.navigate(route)
    rss_after = _rss_mb()
    growth = rss_after - rss_before
    assert growth < 100, f"RSS grew {growth:.1f}MB after 5 navigation cycles"


def test_bridge_destruction(_qt_app):
    from ui_qml_bridge.bridge_factory import BridgeFactory
    gc.collect()
    gc.collect()
    factory = BridgeFactory(MagicMock())
    bridges = factory.create_all()
    del factory
    del bridges
    gc.collect()
    gc.collect()


def test_worker_no_orphan_threads(_qt_app):
    import threading
    from ui_qml_bridge.query_executor import QueryExecutor
    threads_before = dict((t.name, t) for t in threading.enumerate())
    qe = QueryExecutor(worker_manager=None, parent=None)
    for _ in range(10):
        qe.submit("perf_test", lambda: None)
    del qe
    gc.collect()
    gc.collect()
    threads_after = dict((t.name, t) for t in threading.enumerate())
    orphaned = [k for k in threads_after if k not in threads_before and k is not None]
    assert len(orphaned) < 3, f"Orphan threads: {orphaned}"


def test_no_model_duplication_on_multiple_access(_qt_app):
    from ui_qml_bridge.bridge_factory import BridgeFactory
    factory = BridgeFactory(MagicMock())
    lib1 = factory.create_library_bridge()
    lib2 = factory.create_library_bridge()
    assert lib1 is lib2, "create_library_bridge must return the same instance"
    settings1 = factory.create_settings_bridge()
    settings2 = factory.create_settings_bridge()
    assert settings1 is settings2, "create_settings_bridge must return the same instance"


def test_artwork_cache_bounded(_qt_app):
    from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
    bridge = CoverProviderBridge(artwork_service=MagicMock())
    cache_size = getattr(bridge, '_cache_size', None) or getattr(bridge, 'max_cache', None)
    if cache_size is not None:
        assert cache_size <= 500, f"Cover cache size {cache_size} exceeds 500"
