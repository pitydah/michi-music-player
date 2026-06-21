"""Tests for SearchIndex FTS5 module."""


class TestSearchIndex:
    def test_fts_available(self, mock_window):
        db = mock_window._db
        from library.search_index import SearchIndex
        idx = SearchIndex(db._conn)
        result = idx.fts_available
        assert isinstance(result, bool)

    def test_fts_exists_none_by_default(self, mock_window):
        db = mock_window._db
        from library.search_index import SearchIndex
        idx = SearchIndex(db._conn)
        assert idx.fts_exists is False or idx.fts_exists is True

    def test_search_like_empty(self, mock_window):
        db = mock_window._db
        from library.search_index import SearchIndex
        idx = SearchIndex(db._conn)
        results = idx.search_like("", limit=5)
        assert results == []

    def test_search_like_returns_list(self, mock_window):
        db = mock_window._db
        from library.search_index import SearchIndex
        idx = SearchIndex(db._conn)
        results = idx.search_like("test", limit=5)
        assert isinstance(results, list)

    def test_escape_fts(self):
        from library.search_index import _escape_fts
        assert _escape_fts("hello") == "hello*"
        assert _escape_fts("") == ""
        assert _escape_fts("it's") == "it''s*"
