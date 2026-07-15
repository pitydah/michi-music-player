from __future__ import annotations
"""Comprehensive tests for Folders — 10+ tests."""

from unittest.mock import MagicMock

import pytest

from ui_qml.models.FolderTreeModel import FolderTreeModel
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_folders.return_value = 4
    qs.fetch_folders.return_value = [
        {"path": "/music/rock", "name": "rock", "track_count": 10,
         "is_expandable": True, "expanded": False, "source_offline": False,
         "permission_error": False, "removable": True},
        {"path": "/music/jazz", "name": "jazz", "track_count": 5,
         "is_expandable": False, "expanded": False, "source_offline": True,
         "permission_error": False, "removable": False},
        {"path": "/music/classical", "name": "classical", "track_count": 8,
         "is_expandable": True, "expanded": False, "source_offline": False,
         "permission_error": True, "removable": True},
        {"path": "/music/electronic", "name": "electronic", "track_count": 12,
         "is_expandable": True, "expanded": True, "source_offline": False,
         "permission_error": False, "removable": True},
    ]
    return qs


class TestFoldersCompleto:
    def test_initial_state(self, qs):
        m = FolderTreeModel(query_service=qs)
        assert m.count == 0
        assert not m.initialized

    def test_refresh_loads(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        assert m.count == 4
        assert m.totalCount == 4

    def test_role_names(self, qs):
        m = FolderTreeModel(query_service=qs)
        roles = m.roleNames()
        for expected in [b"folderPath", b"folderName", b"trackCount",
                         b"isExpandable", b"expanded"]:
            assert expected in roles.values()

    def test_data_access(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, m.PathRole) == "/music/rock"
        assert m.data(idx, m.NameRole) == "rock"
        assert m.data(idx, m.TrackCountRole) == 10
        assert m.data(idx, m.IsExpandableRole) is True
        assert m.data(idx, m.ExpandedRole) is False

    def test_source_offline_folder(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        idx = m.index(1, 0)
        assert m.data(idx, m.NameRole) == "jazz"
        assert m.data(idx, m.IsExpandableRole) is False

    def test_permission_error_folder(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        idx = m.index(2, 0)
        assert m.data(idx, m.NameRole) == "classical"
        assert m.data(idx, m.IsExpandableRole) is True

    def test_expanded_folder(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        idx = m.index(3, 0)
        assert m.data(idx, m.IsExpandableRole) is True
        assert m.data(idx, m.ExpandedRole) is True

    def test_refresh_with_parent(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh(parent_path="/music/rock")
        assert m.count == 4

    def test_no_query_service(self):
        m = FolderTreeModel()
        assert m._fetch_count() == 0
        assert m._fetch_page(0, 10) == []

    def test_reset(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        assert m.initialized
        m.reset()
        assert not m.initialized
        assert m.count == 0

    def test_cancel(self, qs):
        qe = MagicMock()
        m = FolderTreeModel(query_service=qs, query_executor=qe)
        m.refresh()
        m.cancel()
        assert m.cancelled

    def test_owner(self, qs):
        m = FolderTreeModel(query_service=qs)
        assert m._owner() == "folders"

    def test_folder_with_source_status(self, qs):
        m = FolderTreeModel(query_service=qs)
        m.refresh()
        idx1 = m.index(0, 0)
        assert m.data(idx1, m.IsExpandableRole) is True
        idx2 = m.index(1, 0)
        assert m.data(idx2, m.IsExpandableRole) is False
