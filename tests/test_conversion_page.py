"""Tests for conversion page — structure and nav contracts."""

from __future__ import annotations


class TestConversionNav:
    def test_conversion_route_in_nav_routes(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        assert "audio_lab_conversion" in NAV_ROUTES

    def test_conversion_section_config(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import SECTION_CONFIG
        assert "audio_lab_conversion" in SECTION_CONFIG
        cfg = SECTION_CONFIG["audio_lab_conversion"]
        assert "title" in cfg and "subtitle" in cfg and "icon" in cfg

    def test_conversion_sidebar_key(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("audio_lab_conversion") == "audio_lab"
