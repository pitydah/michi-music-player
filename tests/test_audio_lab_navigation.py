"""Tests: Audio Lab navigation — routes, sidebar active, hub route controller."""

from __future__ import annotations


_ALL_SUBPAGES = (
    "audio_lab_diagnostics",
    "audio_lab_identifier",
    "audio_lab_backup",
    "audio_lab_output",
    "audio_lab_intelligence",
    "audio_lab_musicbrainz",
    "audio_lab_artwork",
    "audio_lab_lyrics",
    "audio_lab_organize",
    "audio_lab_conversion",
    "audio_lab_vinyl_lab",
)

_ALL_HANDLER_METHODS = tuple(
    f"show_{k}" for k in _ALL_SUBPAGES
)

_ALL_WINDOW_METHODS = tuple(
    f"_show_{k}" for k in _ALL_SUBPAGES
)


class TestAudioLabNavigation:

    def test_nav_routes_contain_all_subpages(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        for key in _ALL_SUBPAGES:
            assert key in NAV_ROUTES, f"Missing NAV_ROUTES: {key}"

    def test_section_config_contains_all_subpages(self):
        from ui.controllers.navigation_controller import SECTION_CONFIG
        for key in _ALL_SUBPAGES:
            assert key in SECTION_CONFIG, f"Missing SECTION_CONFIG: {key}"
            cfg = SECTION_CONFIG[key]
            assert "title" in cfg
            assert "subtitle" in cfg
            assert "icon" in cfg

    def test_resolve_sidebar_active_key(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        for key in _ALL_SUBPAGES:
            assert resolve_sidebar_active_key(key) == "audio_lab", f"key={key}"

    def test_hub_route_controller_has_all_show_methods(self):
        from ui.controllers.hub_route_controller import HubRouteController
        for method in _ALL_HANDLER_METHODS:
            assert hasattr(HubRouteController, method), f"Missing: {method}"

    def test_window_has_all_handler_methods(self):
        import ui.window
        for method in _ALL_WINDOW_METHODS:
            assert hasattr(ui.window.MainWindow, method), f"Missing: {method}"

    def test_no_orphan_routes_in_nav_routes(self):
        """Every NAV_ROUTES entry must have a corresponding window handler."""
        from ui.controllers.navigation_controller import NAV_ROUTES
        import ui.window

        for key, method_name in NAV_ROUTES.items():
            assert hasattr(ui.window.MainWindow, method_name), (
                f"Orphan route: {key} → {method_name}"
            )

    def test_sub_hub_identifier_in_page_data(self):
        from ui.audio_lab.sub_pages import AudioLabIdentifierPage
        assert AudioLabIdentifierPage is not None

    def test_sub_hub_backup_in_page_data(self):
        from ui.audio_lab.sub_pages import AudioLabBackupPage
        assert AudioLabBackupPage is not None
