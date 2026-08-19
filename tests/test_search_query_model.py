"""M7.1 — Search query model and normalization — Phase-1 RED tests.

The query model separates RAW QUERY from NORMALIZED QUERY: presentation
must keep showing exactly what the user typed ("Miles Davis", never
"miles davis"), while matching uses a deterministic normalized search
representation (Unicode NFKD -> strip combining marks -> casefold ->
collapse whitespace -> strip -> whitespace tokens).

normalize_search_text is THE single normalization helper — never repeated
inline. SearchQuery is pure, deterministic and immutable.
"""

from michi.domain.search import SearchQuery, normalize_search_text


class TestNormalizeSearchText:
    def test_basic_lowercase(self):
        assert normalize_search_text("Blue") == "blue"

    def test_casefold_upper(self):
        assert normalize_search_text("MILES DAVIS") == "miles davis"

    def test_accent_insensitive(self):
        assert normalize_search_text("Beyoncé") == "beyonce"
        assert normalize_search_text("Sigur Rós") == "sigur ros"

    def test_leading_trailing_whitespace_stripped(self):
        assert normalize_search_text("  miles  ") == "miles"

    def test_multiple_whitespace_collapsed(self):
        assert normalize_search_text("miles    davis") == "miles davis"

    def test_empty_string(self):
        assert normalize_search_text("") == ""

    def test_whitespace_only(self):
        assert normalize_search_text("   ") == ""

    def test_unicode_variants_equivalent(self):
        # Same musical name in different input forms -> same representation.
        assert (
            normalize_search_text("Beyoncé")
            == normalize_search_text("BEYONCE")
            == normalize_search_text("  beyoncé  ")
        )


class TestSearchQuery:
    def test_raw_preserved(self):
        query = SearchQuery.from_raw("  Miles Davis  ")
        assert query.raw == "  Miles Davis  "  # presentation form preserved

    def test_normalized_derived(self):
        query = SearchQuery.from_raw("  Miles   Davis ")
        assert query.normalized == "miles davis"
        assert query.tokens == ("miles", "davis")

    def test_empty_query_inactive(self):
        query = SearchQuery.from_raw("")
        assert query.tokens == ()
        assert query.active is False

    def test_whitespace_only_query_inactive(self):
        query = SearchQuery.from_raw("   ")
        assert query.tokens == ()
        assert query.active is False

    def test_multiple_whitespace_no_empty_tokens(self):
        query = SearchQuery.from_raw("miles    davis")
        assert query.tokens == ("miles", "davis")  # never ("miles", "", "davis")

    def test_single_token(self):
        query = SearchQuery.from_raw("blue")
        assert query.tokens == ("blue",)

    def test_immutable(self):
        query = SearchQuery.from_raw("blue")
        assert query.raw == "blue"
        assert query.normalized == "blue"
        assert query.tokens == ("blue",)
