import pytest
from core.lyrics.parser import parse_lrc, serialize_lrc, parse_plain, normalize_document
from core.lyrics.models import LyricsLine, LyricsDocument


class TestParseLRC:
    def test_empty(self):
        doc = parse_lrc("")
        assert doc.lines == []

    def test_plain_text_goes_to_plain_lines(self):
        doc = parse_lrc("Hello world\nSecond line")
        assert len(doc.lines) == 0
        assert doc.plain_text == "Hello world\nSecond line"

    def test_standard_timestamps(self):
        lrc = "[01:30.50]First line\n[02:00.00]Second line"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 2
        assert doc.lines[0].start_ms == pytest.approx(90500, abs=1)
        assert doc.lines[0].text == "First line"
        assert doc.lines[1].start_ms == pytest.approx(120000, abs=1)
        assert doc.lines[1].text == "Second line"

    def test_short_format(self):
        lrc = "[01:30]No millis"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 1
        assert doc.lines[0].start_ms == 90000

    def test_multi_timestamp(self):
        lrc = "[01:00.00][01:30.00]Same text"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 2
        assert doc.lines[0].start_ms == 60000
        assert doc.lines[1].start_ms == 90000
        assert doc.lines[0].text == "Same text"

    def test_metadata_tags(self):
        lrc = "[ar:Test Artist]\n[al:Test Album]\n[ti:Test Title]\n[la:en]\n[01:00.00]Line"
        doc = parse_lrc(lrc)
        assert doc.metadata.artist == "Test Artist"
        assert doc.metadata.album == "Test Album"
        assert doc.metadata.title == "Test Title"
        assert doc.metadata.language == "en"

    def test_offset_positive(self):
        lrc = "[offset:+500]\n[01:00.00]Line"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == 60500

    def test_offset_negative(self):
        lrc = "[offset:-500]\n[01:00.00]Line"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == 59500

    def test_offset_no_negative_timestamps(self):
        lrc = "[offset:-100000]\n[00:05.00]Line"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms >= 0

    def test_three_digit_minutes(self):
        lrc = "[100:00.00]Long track"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == 6000000

    def test_single_digit_millis(self):
        lrc = "[01:30.5]Test"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == pytest.approx(90500, abs=1)

    def test_two_digit_millis(self):
        lrc = "[01:30.50]Test"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == pytest.approx(90500, abs=1)

    def test_three_digit_millis(self):
        lrc = "[01:30.500]Test"
        doc = parse_lrc(lrc)
        assert doc.lines[0].start_ms == 90500

    def test_skips_unknown_tags(self):
        lrc = "[unknown:value]\n[01:00.00]Line"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 1

    def test_bom_removed(self):
        lrc = "\ufeff[01:00.00]Line"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 1

    def test_crlf(self):
        lrc = "[01:00.00]Line1\r\n[02:00.00]Line2"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 2

    def test_unicode(self):
        lrc = "[01:00.00]Canción en español"
        doc = parse_lrc(lrc)
        assert doc.lines[0].text == "Canción en español"

    def test_malformed_line_skipped(self):
        lrc = "[01:00.00]Valid\nnot a lyric\n[02:00.00]Also valid"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 2

    def test_sorts_by_timestamp(self):
        lrc = "[03:00.00]Third\n[01:00.00]First\n[02:00.00]Second"
        doc = parse_lrc(lrc)
        assert doc.lines[0].text == "First"
        assert doc.lines[1].text == "Second"
        assert doc.lines[2].text == "Third"

    def test_duplicate_timestamps(self):
        lrc = "[01:00.00]A\n[01:00.00]B"
        doc = parse_lrc(lrc)
        assert len(doc.lines) == 2
        assert doc.lines[0].start_ms == doc.lines[1].start_ms


class TestSerializeLRC:
    def test_round_trip(self):
        lrc = "[01:30.500]First line\n[02:00.000]Second line"
        doc = parse_lrc(lrc)
        serialized = serialize_lrc(doc)
        doc2 = parse_lrc(serialized)
        assert len(doc2.lines) == 2
        assert doc2.lines[0].text == "First line"
        assert doc2.lines[0].start_ms == pytest.approx(90500, abs=1)

    def test_preserves_metadata(self):
        doc = LyricsDocument()
        doc.metadata.artist = "Test"
        doc.metadata.album = "Album"
        doc.lines = [LyricsLine(start_ms=60000, text="Line")]
        serialized = serialize_lrc(doc)
        assert "[ar:Test]" in serialized
        assert "[al:Album]" in serialized
        assert "Line" in serialized

    def test_empty_document(self):
        assert serialize_lrc(LyricsDocument()) == ""


class TestParsePlain:
    def test_basic(self):
        doc = parse_plain("Line one\nLine two")
        assert len(doc.lines) == 2
        assert doc.lines[0].text == "Line one"
        assert doc.lines[1].text == "Line two"

    def test_empty(self):
        doc = parse_plain("")
        assert doc.lines == []


class TestNormalizeDocument:
    def test_applies_offset(self):
        doc = LyricsDocument()
        doc.offset_ms = 1000
        doc.lines = [LyricsLine(start_ms=60000, text="Line")]
        normalized = normalize_document(doc)
        assert normalized.lines[0].start_ms == 61000
        assert normalized.offset_ms == 0

    def test_sorts_lines(self):
        doc = LyricsDocument()
        doc.lines = [
            LyricsLine(start_ms=30000, text="B"),
            LyricsLine(start_ms=10000, text="A"),
        ]
        normalized = normalize_document(doc)
        assert normalized.lines[0].text == "A"

    def test_assigns_end_times(self):
        doc = LyricsDocument()
        doc.lines = [
            LyricsLine(start_ms=10000, text="A"),
            LyricsLine(start_ms=20000, text="B"),
        ]
        normalized = normalize_document(doc)
        assert normalized.lines[0].end_ms == 20000
        assert normalized.lines[1].end_ms > 0
