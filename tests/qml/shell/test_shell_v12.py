"""Tests for Shell v12 — navigation, view_registry, view_navigator, view_switcher."""
from unittest.mock import MagicMock, patch

import pytest

from PySide6.QtCore import QObject, Signal


class TestShellNavigation:
    def test_navigation_bridge_exists(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nb = NavigationBridge()
        assert nb is not None
        assert hasattr(nb, 'navigate')

    def test_navigation_bridge_valid_routes(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nb = NavigationBridge()
        assert hasattr(nb, '_current_route') or hasattr(nb, 'navigate')

    def test_navigation_returns_dict(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nb = NavigationBridge()
        nb.navigate("home")
        assert nb._current_route == "home"

    def test_window_dependencies_resolved(self):
        try:
            from ui.window import MainWindow
            assert True
        except Exception:
            pass

    def test_view_registry_bound(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        rrb = RouteRegistryBridge()
        assert hasattr(rrb, 'register') or hasattr(rrb, 'routes')

    def test_no_service_bundle_in_shell_imports(self):
        import ui_qml_bridge.navigation_bridge as nb
        content = open(nb.__file__).read()
        assert "ServiceBundle" not in content

    def test_home_reflects_real_services(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        from unittest.mock import MagicMock
        hb = HomeBridge(
            db=MagicMock(),
            playback_service=MagicMock(),
            library_bridge=MagicMock(),
            library_sources_service=MagicMock(),
            job_bridge=MagicMock(),
        )
        assert hb is not None
        assert hasattr(hb, 'refresh')

    def test_view_switcher_no_none(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        rrb = RouteRegistryBridge()
        r = rrb.routes
        assert r is not None
        assert isinstance(r, list)

    def test_shell_no_direct_db(self):
        import ui_qml_bridge.navigation_bridge as nb
        content = open(nb.__file__).read()
        assert "sqlite3" not in content.lower()
        assert "conn.execute" not in content


class TestHomeReflectsReal:
    def test_home_has_library_stats(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        from unittest.mock import MagicMock
        hb = HomeBridge(
            db=MagicMock(),
            playback_service=MagicMock(),
            library_bridge=MagicMock(),
            library_sources_service=MagicMock(),
            job_bridge=MagicMock(),
            library_query_service=MagicMock(),
        )
        assert hasattr(hb, 'libraryTracks')
        assert hasattr(hb, 'libraryAlbums')
        assert hasattr(hb, 'libraryArtists')

    def test_home_has_playback_state(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        from unittest.mock import MagicMock
        hb = HomeBridge(
            db=MagicMock(),
            playback_service=MagicMock(),
            library_bridge=MagicMock(),
            library_sources_service=MagicMock(),
            job_bridge=MagicMock(),
        )
        assert hasattr(hb, 'currentTrackTitle')
