"""Tests for Global Search v12 — uses GlobalSearchService + QueryExecutor. No fallback sincrono."""
from unittest.mock import MagicMock



class TestGlobalSearchBridgeCreation:
    def test_creation_no_args(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert gs is not None

    def test_creation_with_service(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge(search_service=MagicMock())
        assert gs is not None

    def test_query_default(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert gs.query == ""

    def test_results_default(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert len(gs.results) == 0

    def test_is_searching_default(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert gs.isSearching is False


class TestSearchOperations:
    def test_search_empty(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        result = gs.search("")
        assert result.get("ok")

    def test_search_with_query(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        gs = GlobalSearchBridge(search_service=svc)
        result = gs.search("test")
        assert isinstance(result, dict)

    def test_search_with_query_executor(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        qe = MagicMock()
        qe.submit = MagicMock(return_value=None)
        gs = GlobalSearchBridge(search_service=svc, query_executor=qe)
        result = gs.search("test")
        assert isinstance(result, dict)

    def test_cancel(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        result = gs.cancel()
        assert result.get("ok")

    def test_search_domain(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        gs = GlobalSearchBridge(search_service=svc)
        result = gs.searchDomain("tracks", "test")
        assert isinstance(result, dict)

    def test_score(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        score = gs.searchScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_stale_result_dropped(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert hasattr(gs, 'staleResultDropped')

    def test_partial_results_signal(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        gs = GlobalSearchBridge()
        assert hasattr(gs, 'partialResults')

    def test_no_query_executor_fallback_returns_dict(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": [{"section": "tracks", "title": "Song"}]}
        gs = GlobalSearchBridge(search_service=svc)
        result = gs.search("test")
        assert isinstance(result, dict)
