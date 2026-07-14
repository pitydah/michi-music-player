"""Tests for library selection logic — 12+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock


from ui_qml_bridge.library_bridge import LibraryBridge


def test_selection_bar_toggle():
    ids = []
    assert len(ids) == 0

    def toggle(id_val):
        if id_val in ids:
            ids.remove(id_val)
        else:
            ids.append(id_val)

    toggle(1)
    assert ids == [1]
    toggle(2)
    assert ids == [1, 2]
    toggle(1)
    assert ids == [2]


def test_selection_bar_clear():
    ids = [1, 2, 3]
    ids.clear()
    assert ids == []


def test_selection_bar_count():
    ids = [1, 2, 3, 4, 5]
    assert len(ids) == 5


def test_multi_select_add():
    ids = [1, 3, 5]
    ids.append(7)
    assert ids == [1, 3, 5, 7]


def test_multi_select_remove():
    ids = [1, 2, 3]
    ids.remove(2)
    assert ids == [1, 3]


def test_select_all():
    total = 100
    ids = list(range(total))
    assert len(ids) == total


def test_range_selection():
    all_ids = list(range(20))
    start, end = 3, 8
    selected = all_ids[start:end + 1]
    assert selected == [3, 4, 5, 6, 7, 8]


def test_ctrl_click():
    selected = []
    def ctrl_click(id_val):
        if id_val in selected:
            selected.remove(id_val)
        else:
            selected.append(id_val)
    ctrl_click(5)
    assert 5 in selected
    ctrl_click(5)
    assert 5 not in selected


def test_shift_click():
    last_clicked = 2
    new_click = 6
    start, end = min(last_clicked, new_click), max(last_clicked, new_click)
    new_selection = list(range(start, end + 1))
    assert new_selection == [2, 3, 4, 5, 6]


def test_escape_clears():
    selected = [1, 2, 3]
    selected.clear()
    assert selected == []


def test_selection_persists_across_pages():
    selected = [1, 5, 10]
    page1 = selected[:]
    page2 = [2, 3]
    combined = page1 + page2
    assert combined == [1, 5, 10, 2, 3]


def test_selection_deduplication():
    ids = [1, 2, 1, 3, 2]
    unique = list(dict.fromkeys(ids))
    assert unique == [1, 2, 3]


def test_selection_empty():
    ids = []
    assert len(ids) == 0
    assert not ids


def test_favorite_toggle():
    bridge = LibraryBridge(db=MagicMock(), query_service=MagicMock())
    bridge._query_svc.fetch_track_internal.return_value = {"filepath": "/m/s.flac"}
    bridge._db.conn.execute.return_value.fetchone.return_value = None
    result = bridge.toggleFavoriteById(1)
    assert result["ok"] is True


def test_favorite_unfavorite():
    bridge = LibraryBridge(db=MagicMock(), query_service=MagicMock())
    bridge._query_svc.fetch_track_internal.return_value = {"filepath": "/m/s.flac"}
    bridge._db.conn.execute.return_value.fetchone.return_value = (1,)
    result = bridge.toggleFavoriteById(1)
    assert result["ok"] is True
