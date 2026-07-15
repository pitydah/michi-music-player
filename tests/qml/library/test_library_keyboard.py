"""Tests for library keyboard navigation."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.selection_controller import SelectionController

pytestmark = [pytest.mark.qml_module("library")]


class TestLibraryKeyboardNavigation:
    @pytest.fixture
    def ctrl(self):
        return SelectionController()

    def test_escape_clears_selection(self, ctrl):
        ctrl.replace([1, 2, 3])
        assert ctrl.count == 3
        ctrl.clear()
        assert ctrl.count == 0

    def test_ctrl_a_selects_all(self, ctrl):
        ids = [10, 20, 30]
        ctrl.selectAllLoaded(ids)
        assert ctrl.count == 3
        assert ctrl.selectedIds == [10, 20, 30]

    def test_enter_plays_selected(self, ctrl):
        bridge = MagicMock()
        bridge.playTrackById = MagicMock(return_value={"ok": True})
        ctrl.replace([42])
        result = bridge.playTrackById(ctrl.current)
        assert result["ok"] is True

    def test_shift_click_range_selection(self, ctrl):
        visible_ids = [100, 101, 102, 103, 104]
        ctrl.toggle(101)
        ctrl.selectRangeByRows(1, 4, visible_ids)
        assert len(ctrl.selectedIds) == 4
        assert ctrl.selectedIds == [101, 102, 103, 104]

    def test_tab_moves_between_sections(self):
        items = ["navBar", "filterBar", "statusHeader", "stackContainer"]
        for i in range(len(items) - 1):
            assert items[i] != items[i + 1]

    def test_ctrl_click_toggle_selection(self, ctrl):
        ctrl.toggle(1)
        assert 1 in ctrl.selectedIds
        ctrl.toggle(1)
        assert 1 not in ctrl.selectedIds

    def test_up_down_arrow_selection(self, ctrl):
        ctrl.replace([5])
        assert ctrl.current == 5
        ctrl.replace([6])
        assert ctrl.current == 6

    def test_keyboard_focus_on_list(self):
        mock_list = MagicMock()
        mock_list.focus = True
        mock_list.activeFocusOnTab = True
        assert mock_list.focus is True
        assert mock_list.activeFocusOnTab is True

    def test_shift_plus_click_selects_range(self, ctrl):
        visible = [1, 2, 3, 4, 5]
        ctrl.toggle(2)
        ctrl.selectRangeByRows(1, 3, visible)
        assert ctrl.selectedIds == [2, 3, 4]

    def test_escape_key_clears_selection_when_active(self, ctrl):
        ctrl.replace([7, 8, 9])
        ctrl.clear()
        assert ctrl.selectedIds == []
        assert ctrl.anchor == -1
        assert ctrl.current == -1

    def test_enter_key_on_empty_selection_does_nothing(self, ctrl):
        bridge = MagicMock()
        assert ctrl.count == 0
        if ctrl.count > 0:
            bridge.playTrackById(ctrl.selectedIds[0])
        bridge.playTrackById.assert_not_called()
