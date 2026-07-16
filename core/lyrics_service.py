"""LyricsService — real lyrics fetching from LRC files and network providers."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.lyrics_service")


class LyricsService:
    def __init__(self, lrclib_client=None, worker_manager=None, db=None):
        self._lrclib = lrclib_client
        self._worker_manager = worker_manager
        self._db = db
        self._cache: dict[str, dict] = {}

    @property
    def available(self) -> bool:
        return self._lrclib is not None

    def get_lyrics(self, title: str, artist: str = "",
                   album: str = "", duration: float = 0.0) -> dict:
        cache_key = f"{title}|{artist}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._lrclib:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "lines": [], "plain": ""}

        try:
            result = self._lrclib.get_lyrics(title, artist, album, duration)
            if result:
                data = {
                    "ok": True,
                    "lines": [{"timestamp": line.timestamp, "text": line.text} for line in (result.lines or [])],
                    "plain": result.plain or "",
                    "source": result.source or "lrclib",
                }
                self._cache[cache_key] = data
                return data
            return {"ok": True, "lines": [], "plain": "", "source": "none"}
        except Exception as e:
            logger.error("Lyrics fetch error: %s", e)
            return {"ok": False, "error": str(e), "lines": [], "plain": ""}

    def save_lyrics(self, path: str, lyrics_text: str) -> dict:
        try:
            from pathlib import Path
            p = Path(path)
            lrc_path = p.with_suffix(".lrc")
            lrc_path.write_text(lyrics_text, encoding="utf-8")
            return {"ok": True, "path": str(lrc_path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cancel(self):
        self._cancelled = True

    def start(self):
        self._cancelled = False

    def health(self) -> dict:
        return {"available": self.available, "cache_size": len(self._cache)}

    def shutdown(self):
        self._cache.clear()
