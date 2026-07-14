import sys
import time

import pytest


@pytest.fixture(scope="module")
def _qt_app():
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    return app


def _delta_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


class TestQmlStartupTime:
    def test_import_module_time(self):
        t0 = time.perf_counter()
        import ui_qml_bridge
        elapsed = _delta_ms(t0)
        assert elapsed < 2000, f"import ui_qml_bridge took {elapsed:.1f}ms"
        assert hasattr(ui_qml_bridge, "__file__")

    def test_route_registry_load(self):
        t0 = time.perf_counter()
        from ui_qml_bridge.route_registry import ROUTES
        elapsed = _delta_ms(t0)
        assert elapsed < 500, f"route_registry load took {elapsed:.1f}ms"
        assert len(ROUTES) > 0

    def test_service_bundle_initialization(self):
        t0 = time.perf_counter()
        from ui_qml_bridge.service_bundle import ServiceBundle
        bundle = ServiceBundle()
        elapsed = _delta_ms(t0)
        assert elapsed < 200, f"ServiceBundle init took {elapsed:.1f}ms"
        assert bundle.player_service is None
        assert bundle.db is None

    def test_navigation_bridge_instantiation(self, _qt_app):
        t0 = time.perf_counter()
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        elapsed = _delta_ms(t0)
        assert elapsed < 200, f"NavigationBridge init took {elapsed:.1f}ms"
        assert nav is not None

    def test_bridge_factory_creation(self, _qt_app):
        from ui_qml_bridge.bridge_factory import BridgeFactory
        from ui_qml_bridge.service_bundle import ServiceBundle
        t0 = time.perf_counter()
        factory = BridgeFactory(ServiceBundle())
        elapsed = _delta_ms(t0)
        assert elapsed < 200, f"BridgeFactory init took {elapsed:.1f}ms"
        assert factory is not None

    def test_context_registrar_creation(self, _qt_app):
        t0 = time.perf_counter()
        from ui_qml_bridge.context_registrar import ContextRegistrar
        registrar = ContextRegistrar(None)
        elapsed = _delta_ms(t0)
        assert elapsed < 100, f"ContextRegistrar init took {elapsed:.1f}ms"
        assert registrar is not None

    def test_cover_bridge_import(self, _qt_app):
        t0 = time.perf_counter()
        from ui_qml_bridge.cover_bridge import CoverBridge
        elapsed = _delta_ms(t0)
        assert elapsed < 500, f"CoverBridge import took {elapsed:.1f}ms"
        assert CoverBridge is not None

    def test_full_bridge_factory_phases(self, _qt_app):
        from ui_qml_bridge.bridge_factory import BridgeFactory
        from ui_qml_bridge.service_bundle import ServiceBundle
        factory = BridgeFactory(ServiceBundle())
        t0 = time.perf_counter()
        bridges = factory.create_all()
        elapsed = _delta_ms(t0)
        assert elapsed < 5000, f"BridgeFactory.create_all took {elapsed:.1f}ms"
        assert len(bridges) > 20
        assert "navigation" in bridges
        assert "home" in bridges

    def test_library_query_service_init(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        t0 = time.perf_counter()
        qs = LibraryQueryService(None, db_path=":memory:")
        elapsed = _delta_ms(t0)
        assert elapsed < 1000, f"LibraryQueryService init took {elapsed:.1f}ms"
        assert qs is not None
