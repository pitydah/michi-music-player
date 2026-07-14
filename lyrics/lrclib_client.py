"""LRC Lyrics Client — legacy compatibility wrapper.

Delegates to the new LrcLibProvider under core/lyrics.
Maintains the original public API for backwards compatibility.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from core.lyrics.models import TrackIdentity

logger = logging.getLogger("michi.lyrics.legacy")


@dataclass
class LyricLine:
    timestamp: float
    text: str


@dataclass
class LyricsResult:
    lines: list[LyricLine] = field(default_factory=list)
    plain: str = ""
    source: str = ""


class LrcLibClient:
    BASE = "https://lrclib.net/api"

    def __init__(self):
        self._cache: dict[tuple, Optional[LyricsResult]] = {}
        self._throttle_ts: float = 0.0

    def get_lyrics(self, title: str, artist: str = "",
                   album: str = "", duration: float = 0.0) -> Optional[LyricsResult]:
        key = (title.lower().strip(), artist.lower().strip())

        if key in self._cache:
            return self._cache[key]

        elapsed = time.monotonic() - self._throttle_ts
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        self._throttle_ts = time.monotonic()

        try:
            identity = TrackIdentity(
                title=title, artist=artist, album=album,
                duration_ms=int(duration * 1000),
            )
            from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider as NewProvider
            provider = NewProvider()
            result = provider.resolve(identity)

            if result.ok and result.document:
                legacy = LyricsResult(
                    plain=result.document.plain_text,
                    source="lrclib.net",
                )
                for line in result.document.lines:
                    legacy.lines.append(LyricLine(
                        timestamp=line.start_ms / 1000.0,
                        text=line.text,
                    ))
                if not legacy.lines and not legacy.plain:
                    legacy = None
                self._cache[key] = legacy
                return legacy

            self._cache[key] = None
            return None

        except Exception:
            return None

    def _parse(self, data: dict) -> Optional[LyricsResult]:
        result = LyricsResult()
        synced = data.get("syncedLyrics", "")
        plain = data.get("plainLyrics", "")
        result.plain = plain
        result.source = "lrclib.net"

        if synced:
            result.lines = self._parse_lrc(synced)
            return result
        if plain:
            for i, line in enumerate(plain.strip().splitlines()):
                result.lines.append(LyricLine(
                    timestamp=float(i) * 3.0,
                    text=line.strip(),
                ))
            return result
        return None

    @staticmethod
    def _parse_lrc(lrc_text: str) -> list[LyricLine]:
        from core.lyrics.parser import parse_lrc as new_parse
        doc = new_parse(lrc_text)
        return [LyricLine(
            timestamp=line.start_ms / 1000.0,
            text=line.text,
        ) for line in doc.lines]

    def search(self, query: str) -> list[LyricsResult]:
        try:
            identity = TrackIdentity(title=query)
            from infrastructure.lyrics.providers.lrclib_provider import LrcLibProvider as NewProvider
            provider = NewProvider()
            result = provider.search(identity)
            legacy_results: list[LyricsResult] = []
            for candidate in result.candidates:
                lr = LyricsResult(
                    plain=candidate.plain_text,
                    source="lrclib.net",
                )
                for line in candidate.lines:
                    lr.lines.append(LyricLine(
                        timestamp=line.start_ms / 1000.0,
                        text=line.text,
                    ))
                legacy_results.append(lr)
            return legacy_results[:5]
        except Exception:
            return []
