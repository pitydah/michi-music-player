"""Tests for query parser — key and quality field filters."""

from __future__ import annotations


class TestQueryParser:

    def test_key_filter(self):
        from library.query_parser import parse_query
        q = parse_query("key:Cm")
        assert len(q.terms) == 1
        assert q.terms[0].field == "key"
        assert q.terms[0].value == "Cm"

    def test_quality_filter(self):
        from library.query_parser import parse_query
        q = parse_query("quality:hires")
        assert len(q.terms) == 1
        assert q.terms[0].field == "quality"
        assert q.terms[0].value == "hires"

    def test_quality_lossless(self):
        from library.query_parser import parse_query
        q = parse_query("quality:lossless")
        assert q.terms[0].value == "lossless"

    def test_key_major(self):
        from library.query_parser import parse_query
        q = parse_query("key:Am")
        assert q.terms[0].value == "Am"

    def test_combined_artist_quality(self):
        from library.query_parser import parse_query
        q = parse_query("artist:Genesis quality:lossless")
        assert len(q.terms) == 2
        fields = {t.field for t in q.terms}
        assert "artist" in fields
        assert "quality" in fields

    def test_analysis_filter(self):
        from library.query_parser import parse_query
        q = parse_query("analysis:pending")
        assert len(q.terms) == 1
        assert q.terms[0].field == "analysis_status"
        assert q.terms[0].value == "pending"

    def test_spectral_filter(self):
        from library.query_parser import parse_query
        q = parse_query("spectral:suspicious")
        assert len(q.terms) == 1
        assert q.terms[0].field == "spectral_verdict"
        assert q.terms[0].value == "suspicious"

    def test_spectral_inconclusive(self):
        from library.query_parser import parse_query
        q = parse_query("spectral:inconclusive")
        assert q.terms[0].field == "spectral_verdict"
        assert q.terms[0].value == "inconclusive"
