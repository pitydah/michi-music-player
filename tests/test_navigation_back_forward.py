"""Tests: Navigation — back/forward buttons, Alt+Left/Right, no back buttons in center."""

import os

import pytest


class TestNavigationBackForward:

    def test_shortcut_controller_has_alt_left_right(self):
        """Alt+Left and Alt+Right should be registered in ShortcutController."""
        from ui.controllers.shortcut_controller import ShortcutController
        import inspect
        src = inspect.getsource(ShortcutController.setup)
        assert "Alt+Left" in src
        assert "Alt+Right" in src

    def test_nav_ctrl_has_back_and_forward_methods(self):
        from ui.controllers.navigation_controller import NavigationController
        assert hasattr(NavigationController, 'navigate_back')
        assert hasattr(NavigationController, 'navigate_forward')

    def test_nav_back_btn_disables_when_no_history(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        assert h.can_go_back is False
        assert h.can_go_forward is False

    def test_nav_history_push_and_back(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("home")
        h.push("library")
        assert h.can_go_back is True
        entry = h.back()
        assert entry[0] == "home"
        assert h.can_go_forward is True

    @pytest.mark.parametrize("filepath,pattern", [
        ("ui/album_detail_view.py", "← Volver"),
        ("ui/expanded_view.py", "← Volver"),
        ("ui/audio_lab/sub_pages.py", "Volver a Audio Lab"),
    ])
    def test_no_back_button_in_center_panels(self, filepath, pattern):
        """Central panels should not contain visible back buttons."""
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, filepath)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert pattern not in content, f"{filepath} contains '{pattern}'"

    def test_back_requested_signals_removed(self):
        """back_requested connections should not exist in ui_builder."""
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, "ui/builder/ui_builder.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert ".back_requested.connect" not in content, "back_requested still connected in ui_builder"

    def test_hub_route_michi_disc_lab_no_library_hub(self):
        """show_michi_disc_lab should not build library_hub."""
        from ui.controllers.hub_route_controller import HubRouteController
        import inspect
        src = inspect.getsource(HubRouteController.show_michi_disc_lab)
        assert "LibraryHubPage" not in src

    def test_connections_hub_no_michi_local(self):
        """connections_hub_page should not navigate to michi_local route."""
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.join(root, "ui/hubs/connections_hub_page.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "michi_local" not in content
