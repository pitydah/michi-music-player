"""Tests for ExpandedController."""
from legacy_widgets.ui.controllers.legacy_controllers.expanded_controller import ExpandedController


class TestExpandedController:
    def test_show_no_current(self, mock_window):
        mock_window._playback.current = None
        ctrl = ExpandedController(mock_window)
        ctrl.show_expanded()
        # Should return early without crash

    def test_back(self, mock_window):
        ctrl = ExpandedController(mock_window)
        ctrl.back()
        mock_window._views.show.assert_called_with("library")
        mock_window._section_title.setText.assert_called_with("Biblioteca")
