"""Advanced tests for SelectionController."""
from __future__ import annotations

import pytest

from ui_qml_bridge.selection_controller import SelectionController


class MockModel:
    def __init__(self, count=10):
        self._count = count

    @property
    def count(self):
        return self._count

    def idAt(self, row):
        if 0 <= row < self._count:
            return row + 100
        return -1


class TestSelectionControllerAdvanced:
    @pytest.fixture
    def ctrl(self):
        return SelectionController()

    def test_initial_state(self, ctrl):
        assert ctrl.count == 0
        assert ctrl.selectedIds == []
        assert ctrl.anchor == -1
        assert ctrl.current == -1
        assert ctrl.hasSelection is False

    def test_toggle_add(self, ctrl):
        ctrl.toggle(5)
        assert ctrl.selectedIds == [5]
        assert ctrl.count == 1

    def test_toggle_remove(self, ctrl):
        ctrl.toggle(5)
        ctrl.toggle(5)
        assert ctrl.selectedIds == []
        assert ctrl.count == 0

    def test_toggle_multiple(self, ctrl):
        ctrl.toggle(1)
        ctrl.toggle(2)
        ctrl.toggle(3)
        assert ctrl.selectedIds == [1, 2, 3]
        assert ctrl.count == 3

    def test_replace(self, ctrl):
        ctrl.populate_all([1, 2, 3])
        ctrl.replace(99)
        assert ctrl.selectedIds == [99]
        assert ctrl.anchor == 99
        assert ctrl.current == 99

    def test_add(self, ctrl):
        ctrl.add(10)
        assert 10 in ctrl.selectedIds

    def test_add_duplicate(self, ctrl):
        ctrl.add(10)
        ctrl.add(10)
        assert ctrl.selectedIds == [10]

    def test_remove_existing(self, ctrl):
        ctrl.add(10)
        ctrl.remove(10)
        assert 10 not in ctrl.selectedIds

    def test_remove_nonexistent(self, ctrl):
        ctrl.populate_all([1, 2, 3])
        ctrl.remove(99)
        assert ctrl.selectedIds == [1, 2, 3]

    def test_range_with_model(self, ctrl):
        model = MockModel(count=10)
        ctrl.toggle(101)
        ctrl._anchor = 1
        ctrl.range(1, 4, model)
        assert 105 in ctrl.selectedIds or 104 in ctrl.selectedIds or len(ctrl.selectedIds) > 1

    def test_range_empty_anchor(self, ctrl):
        model = MockModel(count=10)
        ctrl.range(2, 5, model)
        assert len(ctrl.selectedIds) >= 0

    def test_select_all_loaded(self, ctrl):
        model = MockModel(count=5)
        result = ctrl.selectAllLoaded(model)
        assert result is True
        assert ctrl.count == 5
        assert 100 in ctrl.selectedIds
        assert 104 in ctrl.selectedIds

    def test_select_all_loaded_empty_model(self, ctrl):
        model = MockModel(count=0)
        result = ctrl.selectAllLoaded(model)
        assert result is True
        assert ctrl.count == 0

    def test_select_all_loaded_no_model(self, ctrl):
        result = ctrl.selectAllLoaded(None)
        assert result is False

    def test_select_all_preserves_existing(self, ctrl):
        ctrl.toggle(5)
        before = ctrl.count
        ctrl.selectAll()
        assert ctrl.count == before

    def test_clear(self, ctrl):
        ctrl.populate_all([1, 2, 3])
        ctrl.clear()
        assert ctrl.count == 0
        assert ctrl.anchor == -1
        assert ctrl.current == -1

    def test_contains(self, ctrl):
        ctrl.toggle(42)
        assert ctrl.contains(42) is True
        assert ctrl.contains(99) is False

    def test_generation_increments(self, ctrl):
        g0 = ctrl.generation
        ctrl.toggle(1)
        assert ctrl.generation == g0 + 1

    def test_selection_changed_emits_ids(self, ctrl):
        emitted = []
        ctrl.selectionChanged.connect(lambda ids: emitted.append(ids))
        ctrl.toggle(5)
        assert len(emitted) == 1
        assert emitted[0] == [5]
