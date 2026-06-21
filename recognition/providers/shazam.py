"""ShazamProvider — real ShazamIO integration via shazamio library."""
import logging
import asyncio
import contextlib

from recognition.base_recognizer import BaseRecognizer

logger = logging.getLogger("astra.recognition.shazam")


class ShazamProvider(BaseRecognizer):
    """Music recognition via ShazamIO (shazamio Python library).

    Requirements: pip install shazamio
    Does NOT require an API key — uses free Shazam endpoint.
    """

    name = "shazamio"
    requires_api_key = False

    def __init__(self):
        super().__init__()
        self._available = False
        try:
            import importlib.util
            if importlib.util.find_spec("shazamio") is not None:
                self._available = True
        except Exception:
            pass

    def is_configured(self) -> bool:
        return self._available

    def identify(self, sample_bytes=None, source="", filepath=""):
        """Identify audio via ShazamIO.

        If filepath is provided, reads MP3/WAV file directly.
        If sample_bytes is provided, uses raw byte data.
        """
        if not self._available:
            return None

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self._identify_async(sample_bytes, filepath))
            return result
        except Exception as e:
            logger.debug(f"ShazamIO identify failed: {e}")
            return None

    async def _identify_async(self, sample_bytes, filepath):
        from shazamio import Shazam

        shazam = Shazam()

        if filepath:
            out = await shazam.recognize(filepath)
        elif sample_bytes:
            out = await shazam.recognize(data=sample_bytes)
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
