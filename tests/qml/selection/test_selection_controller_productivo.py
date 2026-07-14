"""Productive tests for SelectionController — 15+ tests."""
from __future__ import annotations

import pytest

from ui_qml_bridge.selection_controller import SelectionController


class MockSelectionSource:
    def __init__(self, ids=None, anchor=-1, current=-1, generation=0):
        self._ids = ids or []
        self._anchor = anchor
        self._current = current
        self._generation = generation

    def restore(self):
        return {
            "selected_ids": list(self._ids),
            "anchor": self._anchor,
            "current": self._current,
            "generation": self._generation,
        }


class TestSelectionControllerProductivo:
    @pytest.fixture
    def ctrl(self):
        return SelectionController()

    def test_select_range_by_rows_with_visible_ids(self, ctrl):
        visible = [101, 102, 103, 104, 105]
        ctrl.selectRangeByRows(1, 3, visible)
        assert ctrl.selectedIds == [102, 103, 104]
        assert ctrl.count == 3
        assert ctrl.current == 104

    def test_select_range_by_rows_reverse(self, ctrl):
        visible = [101, 102, 103, 104, 105]
        ctrl.selectRangeByRows(3, 1, visible)
        assert ctrl.selectedIds == [102, 103, 104]
        assert ctrl.count == 3

    def test_select_range_by_rows_single(self, ctrl):
        visible = [101, 102, 103]
        ctrl.selectRangeByRows(1, 1, visible)
        assert ctrl.selectedIds == [102]
        assert ctrl.count == 1

    def test_select_range_by_rows_out_of_bounds(self, ctrl):
        visible = [101, 102]
        ctrl.selectRangeByRows(0, 5, visible)
        assert ctrl.selectedIds == [101, 102]
        assert ctrl.count == 2

    def test_select_range_by_rows_empty(self, ctrl):
        ctrl.selectRangeByRows(0, 2, [])
        assert ctrl.selectedIds == []
        assert ctrl.count == 0

    def test_select_all_loaded_with_ids(self, ctrl):
        ctrl.selectAllLoaded([1, 2, 3, 4, 5])
        assert ctrl.selectedIds == [1, 2, 3, 4, 5]
        assert ctrl.count == 5
        assert ctrl.anchor == 1
        assert ctrl.current == 5

    def test_select_all_loaded_empty(self, ctrl):
        ctrl.selectAllLoaded([])
        assert ctrl.selectedIds == []
        assert ctrl.count == 0

    def test_select_all_filtered(self, ctrl):
        ctrl.selectAllFiltered([10, 20, 30])
        assert ctrl.selectedIds == [10, 20, 30]
        assert ctrl.anchor == 10
        assert ctrl.current == 30

    def test_invert_loaded(self, ctrl):
        ctrl.replace([1, 3, 5])
        ctrl.invertLoaded([1, 2, 3, 4, 5])
        assert sorted(ctrl.selectedIds) == [2, 4]
        assert ctrl.count == 2

    def test_invert_loaded_empty_current(self, ctrl):
        ctrl.invertLoaded([1, 2, 3])
        assert sorted(ctrl.selectedIds) == [1, 2, 3]
        assert ctrl.count == 3

    def test_invert_loaded_all_selected(self, ctrl):
        ctrl.replace([1, 2, 3])
        ctrl.invertLoaded([1, 2, 3])
        assert ctrl.selectedIds == []
        assert ctrl.count == 0

    def test_clear_resets_state(self, ctrl):
        ctrl.replace([1, 2, 3])
        ctrl.clear()
        assert ctrl.count == 0
        assert ctrl.selectedIds == []
        assert ctrl.anchor == -1
        assert ctrl.current == -1
        assert ctrl.hasSelection is False

    def test_clear_generation(self, ctrl):
        ctrl.replace([1, 2])
        ctrl.clearGeneration()
        assert ctrl.generation == 0
        assert ctrl.count == 2

    def test_restore_from_source(self, ctrl):
        source = MockSelectionSource(ids=[10, 20, 30], anchor=10, current=30, generation=5)
        result = ctrl.restore(source)
        assert result["ok"] is True
        assert ctrl.selectedIds == [10, 20, 30]
        assert ctrl.count == 3
        assert ctrl.anchor == 10
        assert ctrl.current == 30

    def test_restore_from_empty_source(self, ctrl):
        ctrl.replace([1, 2])
        source = MockSelectionSource()
        ctrl.restore(source)
        assert ctrl.selectedIds == []
        assert ctrl.count == 0

    def test_restore_from_invalid_source(self, ctrl):
        result = ctrl.restore(None)
        assert result["ok"] is False

    def test_snapshot(self, ctrl):
        ctrl.replace([5, 10, 15])
        snap = ctrl.snapshot()
        assert snap["ok"] is True
        assert snap["selected_ids"] == [5, 10, 15]
        assert snap["anchor"] == 5
        assert snap["current"] == 15
        assert snap["count"] == 3

    def test_snapshot_after_clear(self, ctrl):
        ctrl.replace([1])
        ctrl.clear()
        snap = ctrl.snapshot()
        assert snap["ok"] is True
        assert snap["count"] == 0
        assert snap["selected_ids"] == []

    def test_generation_increment_on_mutate(self, ctrl):
        g0 = ctrl.generation
        ctrl.replace([1])
        assert ctrl.generation == g0 + 1
        ctrl.toggle(2)
        assert ctrl.generation == g0 + 2
        ctrl.clear()
        assert ctrl.generation == g0 + 3

    def test_signal_emission_count(self, ctrl):
        sig_count = [0]
        ctrl.selectionChanged.connect(lambda: sig_count.__setitem__(0, sig_count[0] + 1))
        ctrl.replace([1, 2])
        assert sig_count[0] == 1
        ctrl.toggle(3)
        assert sig_count[0] == 2
        ctrl.clear()
        assert sig_count[0] == 3
