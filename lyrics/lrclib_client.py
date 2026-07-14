"""LRC Lyrics Client — fetches synced lyrics from lrclib.net."""

import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LyricLine:
    timestamp: float  # seconds
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

        # Throttle: at most 1 request per second
        elapsed = time.monotonic() - self._throttle_ts
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        self._throttle_ts = time.monotonic()

        try:
            params = {}
            if artist:
                params["artist_name"] = artist
            if title:
                params["track_name"] = title
            if album:
                params["album_name"] = album
            if duration > 0:
                params["duration"] = str(int(duration))

            url = f"{self.BASE}/get?{urllib.parse.urlencode(params)}"

            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            result = self._parse(data)
            self._cache[key] = result
            return result

        except urllib.error.HTTPError as e:
            if e.code == 404:
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
            # Convert plain text to simple timestamped lines
            for i, line in enumerate(plain.strip().splitlines()):
                result.lines.append(LyricLine(
                    timestamp=float(i) * 3.0,
                    text=line.strip(),
                ))
            return result

        return None

    @staticmethod
    def _parse_lrc(lrc_text: str) -> list[LyricLine]:
        import re
        lines: list[LyricLine] = []

        for line in lrc_text.strip().splitlines():
            # Match [mm:ss.xx] or [mm:ss]
            matches = list(re.finditer(
                r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]", line))
            if not matches:
                # Check for [mm:ss.xx]... multi-timestamp format
                # Try alternative pattern
                matches = list(re.finditer(
                    r"<(\d{2}):(\d{2})\.(\d{1,3})>", line))

            if not matches:
                continue

            text = line[matches[-1].end():].strip()
            if not text:
                continue

            for m in matches:
                minutes = int(m.group(1))
                seconds = int(m.group(2))
                millis = int(m.group(3) or "0")
                ts = minutes * 60.0 + seconds + millis / 1000.0
                lines.append(LyricLine(timestamp=ts, text=text))

        # Sort by timestamp
        lines.sort(key=lambda line: line.timestamp)
        return lines

    def search(self, query: str) -> list[LyricsResult]:
        """Search for tracks and return available lyrics."""
        try:
            url = f"{self.BASE}/search?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MichiMusicPlayer/1.0 (lyrics)")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results: list[LyricsResult] = []
            for entry in data[:5]:
                res = self._parse(entry)
                if res:
                    results.append(res)
            return results

        except Exception:
            return []
