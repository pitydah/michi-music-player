"""Tests for SelectionController — 12+ tests."""
from __future__ import annotations

import pytest

from ui_qml_bridge.selection_controller import SelectionController
import pytest
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def sc():
    return SelectionController()


def test_initial_state(sc):
    assert sc.count == 0
    assert sc.hasSelection is False
    assert sc.selectedIds == []
    assert sc.generation == 0


def test_toggle_selects(sc):
    sc.toggle(1)
    assert sc.count == 1
    assert sc.hasSelection is True
    assert sc.selectedIds == [1]
    assert sc.generation == 1


def test_toggle_deselects(sc):
    sc.toggle(1)
    sc.toggle(1)
    assert sc.count == 0
    assert sc.hasSelection is False
    assert sc.selectedIds == []


def test_toggle_multiple(sc):
    sc.toggle(1)
    sc.toggle(2)
    sc.toggle(3)
    assert sc.count == 3
    assert sc.selectedIds == [1, 2, 3]


def test_toggle_immutability(sc):
    sc.toggle(1)
    ids = sc.selectedIds
    ids.append(99)
    assert sc.selectedIds == [1]


def test_range_selection(sc):
    sc.selectRangeByRows(3, 6, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert sc.count == 4
    assert all(i in sc.selectedIds for i in [4, 5, 6, 7])


def test_range_without_anchor(sc):
    gen_before = sc.generation
    sc.selectRangeByRows(5, 5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert sc.generation > gen_before
    assert sc.selectedIds == [6]


def test_clear_selection(sc):
    sc.toggle(1)
    sc.toggle(2)
    sc.clear()
    assert sc.count == 0
    assert sc.hasSelection is False
    assert sc.selectedIds == []
    assert sc.anchor == -1
    assert sc.current == -1


def test_select_all(sc):
    sc.selectAllLoaded([1, 2, 3, 4, 5])
    assert sc.count == 5
    assert sc.selectedIds == [1, 2, 3, 4, 5]


def test_contains(sc):
    sc.toggle(42)
    assert sc.contains(42) is True
    assert sc.contains(99) is False


def test_generation_increment(sc):
    gen0 = sc.generation
    sc.toggle(1)
    assert sc.generation == gen0 + 1
    sc.toggle(2)
    assert sc.generation == gen0 + 2
    sc.clear()
    assert sc.generation == gen0 + 3


def test_anchor_and_current(sc):
    sc.toggle(10)
    assert sc.anchor == 10
    assert sc.current == 10
    sc.toggle(20)
    assert sc.current == 20
    assert sc.anchor == 10


def test_populate_all_then_toggle(sc):
    sc.replace([1, 2, 3])
    sc.toggle(1)
    assert sc.selectedIds == [2, 3]
    sc.toggle(4)
    assert sc.selectedIds == [2, 3, 4]


def test_double_range(sc):
    sc.selectRangeByRows(2, 5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    first_gen = sc.generation
    sc.selectRangeByRows(5, 8, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert sc.generation > first_gen
    assert all(i in sc.selectedIds for i in [6, 7, 8, 9])


def test_selected_ids_reassignment(sc):
    sc.toggle(1)
    ids_before = sc.selectedIds
    sc.toggle(2)
    ids_after = sc.selectedIds
    assert ids_before is not ids_after
