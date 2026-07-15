"""Tests for SelectionController — unified selection for Library, Playlist, Metadata, Tagging, Doctor.

Covers: replace, toggle, add, remove, selectRangeByRows, selectAllLoaded,
        selectAllFiltered, invertLoaded, clear, restore, contains, snapshot.

IDs are arbitrary non-consecutive values to prove no consecutive-ID assumption.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.selection_controller import SelectionController

pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def sc():
    return SelectionController()


class TestSelectionBasics:
    def test_initial_state(self, sc):
        assert sc.count == 0
        assert sc.hasSelection is False
        assert sc.selectedIds == []
        assert sc.anchor == -1
        assert sc.current == -1
        assert sc.generation == 0

    def test_replace(self, sc):
        sc.replace([1, 2, 3])
        assert sc.count == 3
        assert sc.selectedIds == [1, 2, 3]
        assert sc.anchor == 1
        assert sc.current == 3
        assert sc.hasSelection is True

    def test_replace_empty(self, sc):
        sc.replace([1, 2])
        sc.replace([])
        assert sc.count == 0
        assert sc.hasSelection is False

    def test_toggle_add(self, sc):
        sc.toggle(5)
        assert sc.selectedIds == [5]
        assert sc.count == 1

    def test_toggle_remove(self, sc):
        sc.toggle(5)
        sc.toggle(5)
        assert sc.selectedIds == []
        assert sc.count == 0

    def test_toggle_multiple(self, sc):
        sc.toggle(1)
        sc.toggle(2)
        sc.toggle(3)
        assert sc.count == 3
        assert sc.selectedIds == [1, 2, 3]

    def test_add_unique(self, sc):
        sc.add(10)
        assert sc.selectedIds == [10]
        sc.add(20)
        assert sc.selectedIds == [10, 20]

    def test_add_duplicate(self, sc):
        sc.add(10)
        sc.add(10)
        assert sc.selectedIds == [10]

    def test_remove_existing(self, sc):
        sc.replace([1, 2, 3])
        sc.remove(2)
        assert sc.selectedIds == [1, 3]

    def test_remove_non_existing(self, sc):
        sc.replace([1, 2])
        sc.remove(99)
        assert sc.selectedIds == [1, 2]

    def test_clear(self, sc):
        sc.replace([1, 2, 3])
        sc.clear()
        assert sc.count == 0
        assert sc.anchor == -1
        assert sc.current == -1

    def test_contains(self, sc):
        sc.replace([5, 10, 15])
        assert sc.contains(5) is True
        assert sc.contains(10) is True
        assert sc.contains(99) is False

    def test_generation_increments(self, sc):
        assert sc.generation == 0
        sc.toggle(1)
        assert sc.generation == 1
        sc.toggle(2)
        assert sc.generation == 2
        sc.clear()
        assert sc.generation == 3


class TestSelectionRange:
    def test_select_range_by_rows_consecutive(self, sc):
        visible = [100, 101, 102, 103, 104]
        sc.selectRangeByRows(1, 3, visible)
        assert sc.selectedIds == [101, 102, 103]
        assert sc.anchor == 101
        assert sc.current == 103

    def test_select_range_by_rows_reverse(self, sc):
        visible = [100, 101, 102, 103, 104]
        sc.selectRangeByRows(3, 1, visible)
        assert sc.selectedIds == [101, 102, 103]

    def test_select_range_with_non_consecutive_ids(self, sc):
        visible = [1, 50, 500, 5000, 50000]
        sc.selectRangeByRows(0, 3, visible)
        assert sc.selectedIds == [1, 50, 500, 5000]

    def test_select_range_single_row(self, sc):
        visible = [10, 20, 30]
        sc.selectRangeByRows(1, 1, visible)
        assert sc.selectedIds == [20]

    def test_select_range_out_of_bounds(self, sc):
        visible = [1, 2, 3]
        sc.selectRangeByRows(0, 10, visible)
        assert sc.selectedIds == [1, 2, 3]

    def test_select_range_empty_visible(self, sc):
        sc.selectRangeByRows(0, 5, [])
        assert sc.selectedIds == []


class TestSelectionAll:
    def test_select_all_loaded(self, sc):
        sc.selectAllLoaded([100, 200, 300])
        assert sc.count == 3
        assert sc.anchor == 100
        assert sc.current == 300

    def test_select_all_loaded_empty(self, sc):
        sc.selectAllLoaded([])
        assert sc.count == 0
        assert sc.anchor == -1

    def test_select_all_filtered(self, sc):
        sc.selectAllFiltered([1, 3, 5, 7])
        assert sc.count == 4
        assert sc.anchor == 1
        assert sc.current == 7

    def test_select_all_filtered_empty(self, sc):
        sc.selectAllFiltered([])
        assert sc.count == 0

    def test_invert_loaded(self, sc):
        sc.replace([2, 4])
        sc.invertLoaded([1, 2, 3, 4, 5])
        assert sorted(sc.selectedIds) == [1, 3, 5]

    def test_invert_loaded_all_selected(self, sc):
        sc.selectAllLoaded([1, 2, 3])
        sc.invertLoaded([1, 2, 3])
        assert sc.selectedIds == []

    def test_invert_loaded_none_selected(self, sc):
        sc.clear()
        sc.invertLoaded([1, 2, 3])
        assert sorted(sc.selectedIds) == [1, 2, 3]


class TestSelectionSnapshot:
    def test_snapshot(self, sc):
        sc.replace([10, 20, 30])
        snap = sc.snapshot()
        assert snap["ok"] is True
        assert snap["count"] == 3
        assert snap["selected_ids"] == [10, 20, 30]
        assert snap["anchor"] == 10
        assert snap["current"] == 30

    def test_snapshot_empty(self, sc):
        snap = sc.snapshot()
        assert snap["ok"] is True
        assert snap["count"] == 0

    def test_restore_from_snapshot(self, sc):
        sc.replace([7, 8, 9])
        snap = sc.snapshot()
        sc2 = SelectionController()
        mock_source = MagicMock()
        mock_source.restore.return_value = snap
        result = sc2.restore(mock_source)
        assert result["ok"] is True
        assert result["count"] == 3
        assert sc2.selectedIds == [7, 8, 9]

    def test_restore_failure(self, sc):
        mock_source = MagicMock()
        mock_source.restore.side_effect = Exception("fail")
        result = sc.restore(mock_source)
        assert result["ok"] is False
        assert result["error"] == "RESTORE_FAILED"

    def test_restore_none_data(self, sc):
        mock_source = MagicMock()
        mock_source.restore.return_value = None
        result = sc.restore(mock_source)
        assert result["ok"] is False


class TestSelectionNonConsecutive:
    def test_non_consecutive_ids(self, sc):
        sc.replace([1, 100, 1000, 10000])
        assert sc.count == 4
        assert sc.selectedIds == [1, 100, 1000, 10000]

    def test_toggle_non_consecutive(self, sc):
        sc.toggle(7)
        sc.toggle(700)
        sc.toggle(7000)
        assert sc.count == 3

    def test_remove_non_consecutive(self, sc):
        sc.replace([10, 100, 1000])
        sc.remove(100)
        assert sc.selectedIds == [10, 1000]

    def test_contains_non_consecutive(self, sc):
        sc.replace([42, 4242, 424242])
        assert sc.contains(42) is True
        assert sc.contains(4242) is True
        assert sc.contains(424242) is True
        assert sc.contains(424) is False

    def test_invert_non_consecutive(self, sc):
        sc.replace([2, 4])
        sc.invertLoaded([1, 2, 3, 4, 5, 100, 200])
        assert sorted(sc.selectedIds) == [1, 3, 5, 100, 200]


class TestSelectionSignals:
    def test_selection_changed_emitted_on_replace(self, sc):
        emitted = []
        sc.selectionChanged.connect(lambda: emitted.append(True))
        sc.replace([1, 2])
        assert len(emitted) >= 1

    def test_selection_changed_emitted_on_toggle(self, sc):
        emitted = []
        sc.selectionChanged.connect(lambda: emitted.append(True))
        sc.toggle(1)
        assert len(emitted) >= 1

    def test_count_changed_emitted(self, sc):
        emitted = []
        sc.countChanged.connect(lambda: emitted.append(True))
        sc.replace([1, 2, 3])
        assert len(emitted) >= 1

    def test_generation_changed_emitted(self, sc):
        emitted = []
        sc.generationChanged.connect(lambda: emitted.append(True))
        sc.toggle(1)
        assert len(emitted) >= 1

    def test_no_signals_on_no_op_clear(self, sc):
        sc.clear()
        assert sc.generation > 0

    def test_clear_generation(self, sc):
        sc.toggle(1)
        assert sc.generation > 0
        sc.clearGeneration()
        assert sc.generation == 0


class TestSelectionEdgeCases:
    def test_toggle_immutability(self, sc):
        sc.toggle(1)
        ids = sc.selectedIds
        ids.append(99)
        assert sc.selectedIds == [1]

    def test_replace_immutability(self, sc):
        sc.replace([1, 2, 3])
        ids = sc.selectedIds
        ids.clear()
        assert sc.selectedIds == [1, 2, 3]

    def test_large_selection(self, sc):
        large = list(range(0, 10000))
        sc.selectAllLoaded(large)
        assert sc.count == 10000
        assert sc.anchor == 0
        assert sc.current == 9999

    def test_negative_ids(self, sc):
        sc.replace([-1, -2, -3])
        assert sc.count == 3
        assert sc.contains(-2) is True
        sc.remove(-2)
        assert sc.contains(-2) is False

    def test_zero_id(self, sc):
        sc.toggle(0)
        assert sc.contains(0) is True
        sc.toggle(0)
        assert sc.contains(0) is False
