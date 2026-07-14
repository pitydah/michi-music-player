"""Tests for FolderTreeModel and folder browsing — 8+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml.models.FolderTreeModel import FolderTreeModel


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_folders.return_value = 3
    qs.fetch_folders.return_value = [
        {"path": "/music/rock", "name": "rock", "track_count": 10,
         "is_expandable": True, "expanded": False},
        {"path": "/music/jazz", "name": "jazz", "track_count": 5,
         "is_expandable": False, "expanded": False},
        {"path": "/music/classical", "name": "classical", "track_count": 8,
         "is_expandable": True, "expanded": False},
    ]
    return qs


def test_initial_state(qs):
    m = FolderTreeModel(query_service=qs)
    assert m.count == 0
    assert not m.initialized


def test_refresh_loads_data(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh()
    assert m.count == 3
    assert m.totalCount == 3
    assert m.initialized


def test_role_names(qs):
    m = FolderTreeModel(query_service=qs)
    roles = m.roleNames()
    assert b"folderPath" in roles.values()
    assert b"folderName" in roles.values()
    assert b"trackCount" in roles.values()
    assert b"isExpandable" in roles.values()
    assert b"expanded" in roles.values()


def test_data_access(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, m.PathRole) == "/music/rock"
    assert m.data(idx, m.NameRole) == "rock"
    assert m.data(idx, m.TrackCountRole) == 10
    assert m.data(idx, m.IsExpandableRole) is True
    assert m.data(idx, m.ExpandedRole) is False


def test_folder_without_children(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh()
    idx = m.index(1, 0)
    assert m.data(idx, m.NameRole) == "jazz"
    assert m.data(idx, m.IsExpandableRole) is False


def test_folder_with_children(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh()
    idx = m.index(2, 0)
    assert m.data(idx, m.NameRole) == "classical"
    assert m.data(idx, m.IsExpandableRole) is True


def test_refresh_with_parent(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh(parent_path="/music/rock")
    assert m.count == 3


def test_no_query_service():
    m = FolderTreeModel()
    assert m._fetch_count(parent_path="") == 0
    assert m._fetch_page(0, 10) == []


def test_reset(qs):
    m = FolderTreeModel(query_service=qs)
    m.refresh()
    assert m.initialized
    m.reset()
    assert not m.initialized
    assert m.count == 0


def test_cancel(qs):
    qe = MagicMock()
    m = FolderTreeModel(query_service=qs, query_executor=qe)
    m.refresh()
    m.cancel()
    assert m.cancelled


def test_owner(qs):
    m = FolderTreeModel(query_service=qs)
    assert m._owner() == "folders"
