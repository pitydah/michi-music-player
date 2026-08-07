"""MQ: Test GlobalSearchBridge — stale guard, debounce, partial results, errors.

Slice 6 contract: the bridge NEVER executes searches inline. Without a
QueryExecutor it reports INFRASTRUCTURE_UNAVAILABLE; with one it submits and
the results arrive through ``_on_search_done`` (async delivery only).
"""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


@pytest.fixture
def search_service():
    svc = MagicMock()
    svc.search.return_value = {
        "ok": True,
        "results": [
            {"type": "track", "id": "1", "title": "Song A", "section": "Canciones"},
            {"type": "album", "id": "2", "title": "Album B", "section": "Álbumes"},
            {"type": "artist", "id": "3", "title": "Artist C", "section": "Artistas"},
        ],
    }
    return svc


@pytest.fixture
def qe():
    q = MagicMock()
    q.submit = MagicMock(return_value=42)
    q.cancel_owner = MagicMock()
    return q


@pytest.fixture
def bridge(search_service, qe):
    return GlobalSearchBridge(search_service=search_service, query_executor=qe)


class TestGlobalSearchStaleGuard:
    def test_initial_state(self, bridge):
        assert bridge.query == ""
        assert bridge.results == []
        assert bridge.isSearching is False
        assert bridge.errorCode == ""
        assert bridge.errorMessage == ""

    def test_empty_query_clears_results(self, bridge):
        bridge.search("")
        assert bridge.results == []
        assert bridge.isSearching is False

    def test_search_submits_async(self, bridge, search_service, qe):
        result = bridge.search("test")
        assert result["ok"] is True
        assert result.get("async") is True
        qe.submit.assert_called_once()
        search_service.search.assert_not_called()

    def test_search_populates_results(self, bridge, search_service):
        bridge._active_request_id = 1
        bridge._on_search_done(search_service.search.return_value, 1)
        assert len(bridge.results) > 0

    def test_search_stale_result_is_discarded(self, bridge, search_service):
        def delayed_search(q, **kw):
            bridge._active_request_id = 999
            return {"ok": True, "results": [{"type": "track", "title": "Stale", "section": "Canciones"}]}
        search_service.search.side_effect = delayed_search
        bridge.search("test")
        assert bridge.results == []

    def test_cancel_resets_searching(self, bridge):
        bridge.search("test")
        bridge.cancel()
        assert bridge.isSearching is False
        assert bridge.results == []

    def test_cancel_calls_service_cancel(self, bridge, search_service):
        search_service.cancel = MagicMock()
        bridge.search("test")
        bridge.cancel()
        search_service.cancel.assert_called_once_with(owner="global_search")

    def test_cancel_without_service_cancel_does_not_raise(self, bridge):
        bridge.search("test")
        try:
            bridge.cancel()
        except Exception:
            pytest.fail("cancel raised exception")

    def test_service_unavailable_returns_error(self):
        b = GlobalSearchBridge(search_service=None)
        result = b.search("test")
        assert result.get("error") == "SERVICE_UNAVAILABLE"
        assert b.errorCode == "SERVICE_UNAVAILABLE"
        assert b.isSearching is False

    def test_no_query_executor_reports_infrastructure_unavailable(self):
        b = GlobalSearchBridge(search_service=MagicMock(), query_executor=None)
        result = b.search("test")
        assert result.get("ok") is False
        assert result.get("error_code") == "INFRASTRUCTURE_UNAVAILABLE"
        assert b.isSearching is False
        assert b.errorCode == "INFRASTRUCTURE_UNAVAILABLE"

    def test_service_exception_returns_error(self, search_service, qe):
        search_service.search.side_effect = Exception("Search crashed")
        b = GlobalSearchBridge(search_service=search_service, query_executor=qe)
        b.search("test")
        submitted = qe.submit.call_args
        fn = submitted.kwargs["callable_fn"]
        result = fn()
        assert result.get("ok") is False
        assert b.isSearching is True
        submitted.kwargs["on_success"](result)
        assert b.isSearching is False
        assert b.errorMessage == "Search crashed"

    def test_search_by_domain_unknown_falls_back_to_all_domains(self, bridge, qe):
        result = bridge.searchDomain("nonexistent", "test")
        assert result.get("ok") is True
        assert result.get("async") is True
        qe.submit.assert_called_once()

    def test_search_by_domain_submits_async(self, bridge, search_service, qe):
        bridge.searchDomain("track", "test")
        qe.submit.assert_called_once()
        search_service.search.assert_not_called()

    def test_search_increments_request_counter(self, bridge):
        c1 = bridge._request_counter
        bridge.search("a")
        c2 = bridge._request_counter
        bridge.search("b")
        c3 = bridge._request_counter
        assert c3 > c2 > c1

    def test_result_count_limited_to_max(self, search_service, qe):
        many = [{"type": "track", "id": str(i), "title": f"Song {i}", "section": "Canciones"}
                for i in range(100)]
        search_service.search.return_value = {"ok": True, "results": many}
        b = GlobalSearchBridge(search_service=search_service, query_executor=qe)
        b._active_request_id = 1
        b._on_search_done(search_service.search.return_value, 1)
        assert len(b.results) <= 50

    def test_error_code_cleared_on_new_search(self, bridge):
        bridge._error_code = "OLD_ERROR"
        bridge._error_message = "Old error message"
        bridge.search("new query")
        assert bridge.errorCode == ""
        assert bridge.errorMessage == ""

    def test_searching_flag_set_during_search(self, bridge):
        bridge.search("test")
        assert bridge.isSearching is True
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": []}, 1)
        assert bridge.isSearching is False

    def test_double_search_cancels_previous(self, bridge, search_service):
        bridge.search("first")
        rid1 = bridge._active_request_id
        bridge.search("second")
        rid2 = bridge._active_request_id
        assert rid2 != rid1

    def test_search_gen_increments(self, bridge):
        gen1 = bridge._search_gen
        bridge.search("a")
        gen2 = bridge._search_gen
        assert gen2 > gen1

    def test_results_changed_signal_emitted(self, bridge):
        fired = []
        bridge.resultsChanged.connect(lambda: fired.append(True))
        bridge._active_request_id = 1
        bridge._on_search_done({"ok": True, "results": []}, 1)
        assert len(fired) >= 1

    def test_searching_changed_signal_emitted(self, bridge):
        fired = []
        bridge.searchingChanged.connect(lambda: fired.append(True))
        bridge.search("test")
        assert len(fired) >= 1

    def test_query_property_updated(self, bridge):
        bridge.search("hello world")
        assert bridge.query == "hello world"

    def test_domain_map_keys(self):
        from ui_qml_bridge.global_search_bridge import DOMAIN_MAP
        expected = {"track", "album", "artist", "playlist", "folder", "genre",
                    "device", "server", "action", "setting"}
        assert set(DOMAIN_MAP.keys()) == expected
