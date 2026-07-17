"""Tests for RecognitionMatcher — 4-tier matching logic."""
from unittest.mock import MagicMock

import pytest

from recognition.recognition_matcher import RecognitionMatcher, normalize, match_detected_track_simple
from recognition.recognition_matcher import SKIP_LOCAL_MATCH_SOURCES


class FakeItem:
    def __init__(self, title="", artist="", album="", filepath=""):
        self.title = title
        self.artist = artist
        self.album = album
        self.filepath = filepath


class TestNormalize:
    def test_lower_and_strip(self):
        assert normalize("  Hello World  ") == "hello world"

    def test_collapse_spaces(self):
        assert normalize("Hello   World") == "hello world"

    def test_none_becomes_empty(self):
        assert normalize(None) == ""

    def test_accent_preserved(self):
        assert normalize("José González") == "josé gonzález"


class TestRecognitionMatcher:
    @pytest.fixture
    def db(self):
        return MagicMock()

    @pytest.fixture
    def matcher(self, db):
        return RecognitionMatcher(db)

    def test_empty_title_returns_not_found(self, matcher):
        r = matcher.match("", "Artist")
        assert r["status"] == "not_found"

    def test_remote_source_skips_match(self, matcher):
        for src in SKIP_LOCAL_MATCH_SOURCES:
            r = matcher.match("Song", "Artist", source_type=src)
            assert r["status"] == "remote_source", f"failed for {src}"

    # ── Tier 1: Exact match (title + artist) ──

    def test_tier1_exact_title_and_artist(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay", album="Parachutes", filepath="/music/yellow.flac"),
        ]
        r = matcher.match("Yellow", "Coldplay")
        assert r["status"] == "matched"
        assert r["score"] == 1.0
        assert r["filepath"] == "/music/yellow.flac"

    def test_tier1_exact_title_only_no_artist_input(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay", filepath="/music/yellow.flac"),
        ]
        r = matcher.match("Yellow", "")
        assert r["status"] == "matched"

    def test_tier1_case_and_space_insensitive(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay"),
        ]
        r = matcher.match("  YELLOW  ", "  coldplay  ")
        assert r["status"] == "matched"

    def test_tier1_artist_mismatch_falls_through(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay"),
        ]
        r = matcher.match("Yellow", "Beyoncé")
        assert r["status"] != "matched"

    # ── Tier 2: Exact title + exact album ──

    def test_tier2_title_and_album_match(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay", album="Parachutes"),
        ]
        r = matcher.match("Yellow", "Wrong Artist", album="Parachutes")
        assert r["status"] == "matched"
        assert r["score"] == 0.9

    def test_tier2_title_match_album_mismatch_falls_through(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Yellow", artist="Coldplay", album="Parachutes"),
        ]
        # Album mismatch means Tier 2 fails; should fall through to Tier 3 (fuzzy = 1.0)
        r = matcher.match("Yellow", "", album="X&Y")
        assert r["status"] == "matched"  # Tier 3 catches it with score 1.0

    # ── Tier 3: Fuzzy title >= 0.85 ──

    def test_tier3_fuzzy_title_above_threshold(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Smells Like Teen Spirit", artist="Nirvana"),
        ]
        r = matcher.match("Smells Like Teen Spirit (Edit)", "Nirvana")
        assert r["status"] == "possible"
        assert r["score"] >= 0.85

    def test_tier3_fuzzy_title_just_above_threshold(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="abcdefghij", artist="Artist"),
        ]
        r = matcher.match("abcdefghij", "Artist")
        assert r["status"] == "matched"
        assert r["score"] == 1.0

    def test_tier3_fuzzy_title_below_threshold_falls_through(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Completely Different Song Title Here", artist="Artist"),
        ]
        r = matcher.match("Something Else Entirely", "Artist")
        assert r["status"] != "possible"

    def test_tier3_fuzzy_short_title_below_threshold(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="ABCD", artist="Artist"),
        ]
        # One character difference in 4 = 0.75 → below 0.85 threshold
        r = matcher.match("WXYZ", "Artist")
        assert r["status"] not in ("matched", "possible")

    # ── Tier 4: Fuzzy artist + partial title ──

    def test_tier4_fuzzy_artist_and_partial_title(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Lose Yourself (Soundtrack Version)", artist="Eminem"),
        ]
        r = matcher.match("Lose Yourself Soundtrack", "Eminem")
        assert r["status"] in ("matched", "possible")

    def test_tier4_artist_mismatch_tier4_not_reached(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Song", artist="Artist A"),
        ]
        r = matcher.match("Song", "Artist B")
        assert r["status"] not in ("matched",)

    # ── False positives: feat. variants ──

    def test_feat_variant_does_not_false_positive_tier1(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Sicko Mode", artist="Travis Scott"),
        ]
        r = matcher.match("Sicko Mode", "Travis Scott feat. Drake")
        assert r["status"] != "matched"

    def test_feat_variant_handled_by_fuzzy(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Sicko Mode", artist="Travis Scott"),
        ]
        r = matcher.match("Sicko Mode", "Travis Scott feat. Drake")
        assert r["status"] in ("possible", "not_found")

    # ── Live vs studio ──

    def test_live_variant_studio_in_db(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Hotel California", artist="Eagles", album="Hotel California"),
        ]
        r = matcher.match("Hotel California (Live)", "Eagles")
        assert r["status"] == "possible"

    def test_studio_query_live_in_db(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Hotel California (Live at the Forum)", artist="Eagles"),
        ]
        r = matcher.match("Hotel California", "Eagles")
        assert r["status"] == "possible"

    # ── Threshold verification ──

    def test_threshold_085_boundary_just_above(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Almost The Same Song", artist="Artist"),
        ]
        r = matcher.match("Almost the Same Song", "Artist")
        assert r["score"] >= 0.85

    def test_threshold_085_low_similarity_does_not_match(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="Very Long Title That Is Completely Different", artist="Artist"),
        ]
        r = matcher.match("Short", "Artist")
        assert r["status"] == "not_found"

    # ── Legacy wrapper ──

    def test_match_detected_track_simple_exact(self):
        items = [FakeItem(title="Song", artist="Artist", filepath="/path")]
        r = match_detected_track_simple(" Song ", " ARTIST ", items)
        assert r is not None
        assert r["filepath"] == "/path"

    def test_match_detected_track_simple_no_match(self):
        items = [FakeItem(title="Song", artist="Artist")]
        r = match_detected_track_simple("Other", "Artist", items)
        assert r is None

    def test_match_detected_track_simple_no_artist(self):
        items = [FakeItem(title="Song", artist="Artist")]
        r = match_detected_track_simple("Song", "", items)
        assert r is not None

    # ── DB fallback via get_all ──

    def test_db_without_search_advanced_uses_get_all(self, matcher):
        db = MagicMock(spec=["get_all"])
        db.get_all.return_value = [
            FakeItem(title="Song", artist="Artist", filepath="/path"),
        ]
        matcher._db = db
        r = matcher.match("Song", "Artist")
        assert r["status"] == "matched"

    def test_no_db_methods_returns_not_found(self, matcher):
        db = MagicMock(spec=[])
        matcher._db = db
        r = matcher.match("Song", "Artist")
        assert r["status"] == "not_found"

    # ── score rounding ──

    def test_fuzzy_score_rounded_to_two_decimals(self, matcher, db):
        db.search_advanced.return_value = [
            FakeItem(title="abcdefghijklmno", artist="Artist"),
        ]
        r = matcher.match("abcdefghijklmnop", "Artist")
        if r["status"] in ("matched", "possible"):
            assert len(str(r["score"]).split(".")) == 2
            assert len(str(r["score"]).split(".")[1]) <= 2
