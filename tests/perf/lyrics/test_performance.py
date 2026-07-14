"""Performance benchmarks for Lyrics Core V2."""

import time

from core.lyrics.parser import parse_lrc, serialize_lrc
from core.lyrics.timeline import LyricsTimeline
from core.lyrics.models import LyricsDocument, LyricsLine, TrackIdentity
from core.lyrics.matcher import compute_match_score


def _generate_lrc_lines(count: int) -> str:
    lines = []
    for i in range(count):
        sec = i * 5
        m = sec // 60
        s = sec % 60
        lines.append(f"[{m:02d}:{s:02d}.000]Line number {i}")
    return "\n".join(lines)


class TestParsePerformance:
    def test_parse_1000_lines(self):
        lrc = _generate_lrc_lines(1000)
        start = time.monotonic()
        doc = parse_lrc(lrc)
        elapsed = (time.monotonic() - start) * 1000
        assert len(doc.lines) == 1000
        assert elapsed < 200, f"Parse 1000 lines took {elapsed:.1f}ms (limit 200ms)"

    def test_parse_10000_lines(self):
        lrc = _generate_lrc_lines(10000)
        start = time.monotonic()
        doc = parse_lrc(lrc)
        elapsed = (time.monotonic() - start) * 1000
        assert len(doc.lines) == 10000
        assert elapsed < 2000, f"Parse 10000 lines took {elapsed:.1f}ms (limit 2000ms)"


class TestSerializePerformance:
    def test_serialize_1000_lines(self):
        lrc = _generate_lrc_lines(1000)
        doc = parse_lrc(lrc)
        start = time.monotonic()
        serialized = serialize_lrc(doc)
        elapsed = (time.monotonic() - start) * 1000
        assert len(serialized) > 0
        assert elapsed < 100, f"Serialize 1000 lines took {elapsed:.1f}ms (limit 100ms)"


class TestTimelinePerformance:
    def test_10000_active_line_lookups(self):
        lines = [(i * 1000, (i + 1) * 1000, f"Line {i}") for i in range(1000)]
        doc = LyricsDocument()
        doc.lines = [LyricsLine(start_ms=s, end_ms=e, text=t) for s, e, t in lines]
        tl = LyricsTimeline(doc)

        start = time.monotonic()
        for i in range(10000):
            tl.active_line(i * 100)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000, f"10k lookups took {elapsed:.1f}ms (limit 1000ms)"


class TestMatchingPerformance:
    def test_match_100_candidates(self):
        identity = TrackIdentity(title="Test Song", artist="Test Artist", duration_ms=240000)
        candidates = []
        for i in range(100):
            doc = LyricsDocument()
            doc.metadata.title = f"Test Song {i}"
            doc.metadata.artist = "Test Artist"
            doc.duration_ms = 240000 + i * 1000
            candidates.append(doc)

        start = time.monotonic()
        for c in candidates:
            compute_match_score(identity, c)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 500, f"Match 100 candidates took {elapsed:.1f}ms (limit 500ms)"
