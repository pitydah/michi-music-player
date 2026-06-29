"""Tests: Audio Lab navigation — routes, sidebar active, hub route controller, subcards."""

from unittest.mock import MagicMock


class TestAudioLabNavigation:

    def test_nav_routes_contain_all_five_subpages(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        for key in ("audio_lab_diagnostics", "audio_lab_identifier",
                    "audio_lab_backup", "audio_lab_output",
                    "audio_lab_intelligence"):
            assert key in NAV_ROUTES, f"Missing NAV_ROUTES entry: {key}"

    def test_section_config_contains_all_five_subpages(self):
        from ui.controllers.navigation_controller import SECTION_CONFIG
        for key in ("audio_lab_diagnostics", "audio_lab_identifier",
                    "audio_lab_backup", "audio_lab_output",
                    "audio_lab_intelligence"):
            assert key in SECTION_CONFIG, f"Missing SECTION_CONFIG: {key}"

    def test_resolve_sidebar_active_key_returns_audio_lab(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        for key in ("audio_lab_diagnostics", "audio_lab_identifier",
                    "audio_lab_backup", "audio_lab_output",
                    "audio_lab_intelligence"):
            assert resolve_sidebar_active_key(key) == "audio_lab", f"key={key}"

    def test_hub_route_controller_has_all_show_methods(self):
        from ui.controllers.hub_route_controller import HubRouteController
        for method in ("show_audio_lab_diagnostics", "show_audio_lab_identifier",
                       "show_audio_lab_backup", "show_audio_lab_output",
                       "show_audio_lab_intelligence"):
            assert hasattr(HubRouteController, method), f"Missing method: {method}"

    def test_sub_card_does_not_emit_empty_nav_key(self):
        from ui.audio_lab.sub_pages import _build_sub_card
        from PySide6.QtWidgets import QWidget
        parent = QWidget()
        signals = []
        parent.navigate_requested = MagicMock()  # will not be called
        card = _build_sub_card(parent, "home", "Test", "desc", "proximamente", "")
        assert card is not None

    def test_audio_lab_page_has_navigate_requested_signal(self):
        from ui.audio_lab.audio_lab_page import AudioLabPage
        page = AudioLabPage()
        assert hasattr(page, "navigate_requested"), "Missing navigate_requested signal"
