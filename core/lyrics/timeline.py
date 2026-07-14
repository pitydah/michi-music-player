from __future__ import annotations

import bisect

from core.lyrics.models import LyricsLine, LyricsDocument


class LyricsTimeline:
    def __init__(self, doc: LyricsDocument | None = None):
        self._lines: list[LyricsLine] = []
        self._start_times: list[float] = []
        if doc is not None:
            self.load(doc)

    def load(self, doc: LyricsDocument):
        self._lines = list(doc.lines)
        self._lines.sort(key=lambda ln: ln.start_ms)
        self._start_times = [ln.start_ms for ln in self._lines]

    def active_line(self, position_ms: float) -> LyricsLine | None:
        if not self._lines:
            return None
        idx = self.active_index(position_ms)
        if idx is None:
            return None
        return self._lines[idx]

    def active_index(self, position_ms: float) -> int | None:
        if not self._lines:
            return None
        idx = bisect.bisect_right(self._start_times, position_ms) - 1
        if idx < 0:
            return 0
        if idx >= len(self._lines):
            return len(self._lines) - 1
        line = self._lines[idx]
        if line.end_ms > 0 and position_ms > line.end_ms:
            return idx + 1 if idx + 1 < len(self._lines) else idx
        return idx

    def previous_line(self, position_ms: float) -> LyricsLine | None:
        if not self._lines:
            return None
        idx = self.active_index(position_ms)
        if idx is None or idx <= 0:
            return None
        return self._lines[idx - 1]

    def next_line(self, position_ms: float) -> LyricsLine | None:
        if not self._lines:
            return None
        idx = self.active_index(position_ms)
        if idx is None or idx >= len(self._lines) - 1:
            return None
        return self._lines[idx + 1]

    def range(self, start_ms: float, end_ms: float) -> list[LyricsLine]:
        if not self._lines:
            return []
        result = []
        for line in self._lines:
            if line.end_ms > 0 and line.end_ms < start_ms:
                continue
            if line.start_ms > end_ms:
                break
            result.append(line)
        return result

    @property
    def lines(self) -> list[LyricsLine]:
        return list(self._lines)

    @property
    def is_empty(self) -> bool:
        return len(self._lines) == 0

    @property
    def duration_ms(self) -> float:
        if not self._lines:
            return 0.0
        return self._lines[-1].end_ms if self._lines[-1].end_ms > 0 else self._lines[-1].start_ms + 5000
