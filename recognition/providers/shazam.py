"""ShazamProvider — real ShazamIO integration via shazamio library."""
import logging
import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor

from recognition.base_recognizer import BaseRecognizer

logger = logging.getLogger("michi.recognition.shazam")

_SHARED_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="shazam")


class ShazamProvider(BaseRecognizer):
    """Music recognition via ShazamIO (shazamio Python library).

    Requirements: pip install shazamio
    Does NOT require an API key — uses free Shazam endpoint.
    Runs async ShazamIO calls in a background thread to avoid blocking Qt.
    """

    name = "shazamio"
    requires_api_key = False

    def __init__(self):
        super().__init__()
        self._available = False
        self._shazam = None
        try:
            import importlib.util
            if importlib.util.find_spec("shazamio") is not None:
                self._available = True
        except Exception:
            pass

    def is_configured(self) -> bool:
        return self._available

    def identify(self, sample_bytes=None, source="", filepath=""):
        """Identify audio via ShazamIO, runs in background thread."""
        if not self._available:
            return None

        future = _SHARED_EXECUTOR.submit(
            self._identify_sync, sample_bytes, filepath)
        try:
            return future.result(timeout=30)
        except Exception as e:
            logger.debug("ShazamIO identify failed: %s", e)
            return None

    def _identify_sync(self, sample_bytes, filepath):
        """Run async shazamio in a fresh event loop on this thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self._identify_async(sample_bytes, filepath))
        finally:
            loop.close()

    async def _identify_async(self, sample_bytes, filepath):
        from shazamio import Shazam

        if self._shazam is None:
            self._shazam = Shazam()

        if filepath:
            out = await self._shazam.recognize(filepath)
        elif sample_bytes:
            out = await self._shazam.recognize(data=sample_bytes)
        else:
            return None

        track = out.get("track", {})
        if not track:
            return None

        title = track.get("title", "")
        artist = track.get("subtitle", "")

        sections = track.get("sections", [])
        metadata = {}
        for s in sections:
            if s.get("type") == "SONG":
                md = s.get("metadata", [])
                for m in md:
                    metadata[m.get("title", "")] = m.get("text", "")

        album = metadata.get("Album", metadata.get("Álbum", ""))
        genre = metadata.get("Genre", metadata.get("Género", ""))
        year_str = metadata.get("Released", metadata.get("Lanzamiento", ""))
        year = 0
        with contextlib.suppress(ValueError, TypeError):
            year = int(year_str) if year_str else 0

        artwork_url = track.get("images", {}).get("coverarthq", "")

        return {
            "title": title,
            "artist": artist,
            "album": album or "",
            "year": year,
            "genre": genre or "",
            "confidence": 0.8,
            "provider": self.name,
            "source": "shazam",
            "external_url": track.get("url", ""),
            "artwork_url": artwork_url or "",
            "raw_json": out,
        }

    def test_connection(self) -> tuple[bool, str]:
        if not self._available:
            return False, "shazamio library not installed"
        return True, "ShazamIO ready"
