"""Tests: Query parser advanced fields — bpm, sample_rate, channels, bit_depth, key, quality."""

from library.query_parser import parse_query, FieldOp


class TestQueryParserAdvancedFields:

    def test_bpm_gt_120(self):
        q = parse_query("bpm:>120")
        assert len(q.terms) == 1
        assert q.terms[0].field == "bpm"
        assert q.terms[0].op == FieldOp.GT
        assert q.terms[0].value == "120"

    def test_sample_rate_gte_48000(self):
        q = parse_query("sample_rate:>=48000")
        assert q.terms[0].field == "sample_rate"
        assert q.terms[0].op == FieldOp.GTE
        assert q.terms[0].value == "48000"

    def test_channels_eq_2(self):
        q = parse_query("channels:2")
        assert q.terms[0].field == "channels"
        assert q.terms[0].op == FieldOp.EQ
        assert q.terms[0].value == "2"

    def test_bit_depth_eq_24(self):
        q = parse_query("bit_depth:24")
        assert q.terms[0].field == "bit_depth"
        assert q.terms[0].value == "24"

    def test_key_am(self):
        q = parse_query("key:Am")
        assert q.terms[0].field == "key"
        assert q.terms[0].value == "Am"

    def test_quality_lossless(self):
        q = parse_query("quality:lossless")
        assert q.terms[0].field == "quality"
        assert q.terms[0].value == "lossless"

    def test_format_flac(self):
        q = parse_query("format:flac")
        assert q.terms[0].field == "format"
        assert q.terms[0].value == "flac"

    def test_free_text_preserved_with_fields(self):
        q = parse_query('artist:Miles Davis year:>1960 kind:jazz')
        assert "Miles Davis" in q.freetext
        assert len(q.terms) == 2

    def test_field_not_recognized_falls_to_freetext(self):
        q = parse_query("unknown_field:value rest")
        assert "unknown_field:value" in q.freetext
