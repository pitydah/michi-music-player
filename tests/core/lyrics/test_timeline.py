from core.lyrics.timeline import LyricsTimeline
from core.lyrics.models import LyricsDocument, LyricsLine


def make_doc(lines: list[tuple[float, float, str]]) -> LyricsDocument:
    doc = LyricsDocument()
    doc.lines = [
        LyricsLine(start_ms=s, end_ms=e, text=t, line_id=str(i))
        for i, (s, e, t) in enumerate(lines)
    ]
    return doc


class TestLyricsTimeline:
    def test_empty_returns_none(self):
        tl = LyricsTimeline()
        assert tl.active_line(0) is None
        assert tl.active_index(0) is None

    def test_active_line_at_position(self):
        doc = make_doc([(1000, 2000, "A"), (2000, 3000, "B")])
        tl = LyricsTimeline(doc)
        assert tl.active_line(1500).text == "A"
        assert tl.active_line(2000).text == "B"
        assert tl.active_line(2500).text == "B"

    def test_before_first_line(self):
        doc = make_doc([(1000, 2000, "A")])
        tl = LyricsTimeline(doc)
        assert tl.active_line(0).text == "A"
        assert tl.active_index(0) == 0

    def test_after_last_line(self):
        doc = make_doc([(1000, 2000, "A")])
        tl = LyricsTimeline(doc)
        assert tl.active_line(5000).text == "A"
        assert tl.active_index(5000) == 0

    def test_previous_line(self):
        doc = make_doc([(1000, 2000, "A"), (2000, 3000, "B")])
        tl = LyricsTimeline(doc)
        assert tl.previous_line(2500).text == "A"
        assert tl.previous_line(1500) is None

    def test_next_line(self):
        doc = make_doc([(1000, 2000, "A"), (2000, 3000, "B")])
        tl = LyricsTimeline(doc)
        assert tl.next_line(1500).text == "B"
        assert tl.next_line(2500) is None

    def test_range(self):
        doc = make_doc([
            (1000, 2000, "A"),
            (2000, 3000, "B"),
            (3000, 4000, "C"),
        ])
        tl = LyricsTimeline(doc)
        result = tl.range(1500, 2500)
        assert len(result) == 2
        assert result[0].text == "A"
        assert result[1].text == "B"

    def test_no_gap_between_lines(self):
        doc = make_doc([(1000, 0, "A"), (2000, 0, "B")])
        tl = LyricsTimeline(doc)
        assert tl.active_line(1500).text == "A"
        assert tl.active_line(2000).text == "B"

    def test_seek_backwards(self):
        doc = make_doc([
            (1000, 2000, "A"),
            (2000, 3000, "B"),
            (3000, 4000, "C"),
        ])
        tl = LyricsTimeline(doc)
        assert tl.active_line(3500).text == "C"
        assert tl.active_line(1500).text == "A"

    def test_is_empty(self):
        assert LyricsTimeline().is_empty is True
        assert LyricsTimeline(make_doc([(1000, 2000, "A")])).is_empty is False

    def test_duration(self):
        doc = make_doc([(1000, 2000, "A"), (2000, 3000, "B")])
        tl = LyricsTimeline(doc)
        assert tl.duration_ms >= 3000

    def test_large_scale_performance(self):
        lines = [(i * 1000, (i + 1) * 1000, f"Line {i}") for i in range(10000)]
        doc = make_doc(lines)
        tl = LyricsTimeline(doc)
        import time
        start = time.monotonic()
        for _ in range(10000):
            tl.active_line(5000000)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000, f"10k lookups took {elapsed}ms (p95 should be <1ms)"

    def test_empty_range(self):
        doc = make_doc([(1000, 2000, "A")])
        tl = LyricsTimeline(doc)
        assert tl.range(5000, 6000) == []
