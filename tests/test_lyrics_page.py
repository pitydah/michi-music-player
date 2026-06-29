"""Tests for lyrics page — structure and nav contracts."""

from __future__ import annotations


class TestLyricsNav:
    def test_lyrics_route_in_nav_routes(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        assert "audio_lab_lyrics" in NAV_ROUTES

    def test_lyrics_section_config(self):
        from ui.controllers.navigation_controller import SECTION_CONFIG
        assert "audio_lab_lyrics" in SECTION_CONFIG
        cfg = SECTION_CONFIG["audio_lab_lyrics"]
        assert "title" in cfg and "subtitle" in cfg and "icon" in cfg

    def test_lyrics_sidebar_key(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("audio_lab_lyrics") == "audio_lab"
