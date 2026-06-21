"""Tests for SearchEngine module."""


class TestSearchEngine:
    def test_parse_query_simple(self, mock_window):
        from library.query_parser import parse_query
        result = parse_query("hello world")
        assert result.freetext == "hello world"
        assert len(result.terms) == 0

    def test_parse_query_field(self, mock_window):
        from library.query_parser import parse_query
        result = parse_query("artist:Genesis album:Invisible")
        assert "artist" in [t.field for t in result.terms]
        assert "album" in [t.field for t in result.terms]
        values = {t.field: t.value for t in result.terms}
        assert values["artist"] == "Genesis"
        assert values["album"] == "Invisible"

    def test_parse_query_quoted(self, mock_window):
        from library.query_parser import parse_query
        result = parse_query('album:"The Lamb Lies Down" free text')
        assert result.freetext == "free text"
        assert result.terms[0].value == "The Lamb Lies Down"

    def test_parse_query_operator(self, mock_window):
        from library.query_parser import parse_query
        result = parse_query("year:>2000 bitrate:>=320")
        ops = {t.field: t.op.value for t in result.terms}
        assert ops.get("year") == ">"
        assert ops.get("bitrate") == ">="

    def test_parse_query_format(self, mock_window):
        from library.query_parser import parse_query
        result = parse_query("format:flac")
        assert result.terms[0].field == "ext"
        assert result.terms[0].value == "flac"

    def test_search_like_fallback(self, mock_window):
        db = mock_window._db
        from library.search_engine import SearchEngine
        engine = SearchEngine(db._conn)
        results = engine.search("test_query", limit=5)
        assert isinstance(results, list)

    def test_count(self, mock_window):
        db = mock_window._db
        from library.search_engine import SearchEngine
        engine = SearchEngine(db._conn)
        count = engine.count()
        assert isinstance(count, int)
        assert count >= 0
