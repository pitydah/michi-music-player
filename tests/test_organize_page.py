"""Tests for organize page — structure and nav contracts."""

from __future__ import annotations


class TestOrganizeNav:
    def test_organize_route_in_nav_routes(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        assert "audio_lab_organize" in NAV_ROUTES

    def test_organize_section_config(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import SECTION_CONFIG
        assert "audio_lab_organize" in SECTION_CONFIG
        cfg = SECTION_CONFIG["audio_lab_organize"]
        assert "title" in cfg and "subtitle" in cfg and "icon" in cfg

    def test_organize_sidebar_key(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("audio_lab_organize") == "audio_lab"

    def test_update_filepath_exists(self):
        from library.library_db import LibraryDB
        assert hasattr(LibraryDB, 'update_filepath')
