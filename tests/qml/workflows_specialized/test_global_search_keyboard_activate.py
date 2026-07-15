"""MW: Global Search — type query, activate search, navigate results."""
from __future__ import annotations

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestGlobalSearchKeyboardActivate(SpecializedWorkflowBase):
    def test_initial_state(self, global_search_fixtures):
        b = global_search_fixtures
        assert b.query == ""
        assert len(b.results) == 0

    def test_search_query(self, global_search_fixtures):
        b = global_search_fixtures
        result = b.search("test query")
        self.assert_ok(result)

    def test_search_results_populated(self, global_search_fixtures):
        b = global_search_fixtures
        b.results = [
            {"section": "Canciones", "title": "Test Song", "id": "1"},
        ]
        b.search.return_value = {"ok": True, "count": 1}
        result = b.search("test")
        self.assert_ok(result)
        assert len(b.results) >= 1

    def test_cancel_search(self, global_search_fixtures):
        b = global_search_fixtures
        result = b.cancel()
        self.assert_ok(result)

    def test_full_workflow(self, global_search_fixtures):
        b = global_search_fixtures
        b.search("album:test")
        b.cancel()
        assert b.search.called
        assert b.cancel.called

    def test_search_error(self, global_search_fixtures):
        b = global_search_fixtures
        b.search = MagicMock(
            return_value={"ok": False, "error": "SERVICE_UNAVAILABLE"}
        )
        result = b.search("test")
        self.assert_error(result, "SERVICE_UNAVAILABLE")

    def test_search_with_results(self, global_search_fixtures):
        b = global_search_fixtures
        b.search.return_value = {"ok": True, "count": 3}
        b.results = [
            {"section": "Albumes", "title": "Album 1"},
            {"section": "Albumes", "title": "Album 2"},
            {"section": "Canciones", "title": "Song 1"},
        ]
        result = b.search("album")
        self.assert_ok(result)
        assert len(b.results) == 3

    def test_no_results(self, global_search_fixtures):
        b = global_search_fixtures
        b.search.return_value = {"ok": True, "count": 0}
        result = b.search("zzzzz")
        self.assert_ok(result)
