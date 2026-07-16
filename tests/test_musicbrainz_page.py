"""Tests for MusicBrainz page — structure and nav contracts."""

from __future__ import annotations


class TestMusicBrainzNav:
    def test_musicbrainz_route_in_nav_routes(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        assert "audio_lab_musicbrainz" in NAV_ROUTES

    def test_musicbrainz_section_config(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import SECTION_CONFIG
        assert "audio_lab_musicbrainz" in SECTION_CONFIG
        cfg = SECTION_CONFIG["audio_lab_musicbrainz"]
        assert "title" in cfg and "subtitle" in cfg and "icon" in cfg

    def test_musicbrainz_sidebar_key(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("audio_lab_musicbrainz") == "audio_lab"
