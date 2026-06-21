"""Recognition matcher — enhanced cross-referencing with local library."""
import difflib
import logging

logger = logging.getLogger("astra.recognition.matcher")

# Sources that should never be matched against local library
# (radio, streams, remote — they are NOT in the local DB)
SKIP_LOCAL_MATCH_SOURCES = frozenset({
    "radio", "remote_stream", "navidrome", "jellyfin",
})


def normalize(s: str) -> str:
    return " ".join(str(s or "").lower().strip().split())


class RecognitionMatcher:
    """Cross-reference detected tracks with the local library."""

    def __init__(self, db):
        self._db = db

    def match(self, title: str, artist: str, album: str = "",
              source_type: str = "") -> dict:
        """Match a detected track against the local library.

        Args:
            title: Detected track title
            artist: Detected track artist
            album: Detected track album
            source_type: Source type (radio, navidrome, local_file, etc.)

        Returns:
            dict with keys: status, filepath, title, artist, album, score
        """
        result = {
            "status": "not_found",
            "filepath": "",
            "title": "",
            "artist": "",
            "album": "",
            "score": 0.0,
        }

        if not title:
            return result

        # Don't try to match radio/stream tracks against local library
        if source_type in SKIP_LOCAL_MATCH_SOURCES:
            result["status"] = "remote_source"
            return result

        nt = normalize(title)
        na = normalize(artist) if artist else ""
        nalbum = normalize(album) if album else ""

        items = self._db.get_all(search=nt) if hasattr(self._db, 'get_all') else []

        # Tier 1: Exact title + artist
        for item in items:
            it = normalize(item.title or "")
            ia = normalize(item.artist or "") if hasattr(item, 'artist') else ""
            if it == nt and (not na or ia == na):
                result.update(
                    status="matched", filepath=getattr(item, 'filepath', ''),
                    title=item.title or "", artist=getattr(item, 'artist', ''),
                    album=getattr(item, 'album', ''), score=1.0)
                return result

        # Tier 2: Exact title + exact album
        if nalbum:
            for item in items:
                it = normalize(item.title or "")
                ia = normalize(getattr(item, 'album', '') or "")
                if it == nt and ia == nalbum:
                    result.update(
                        status="matched", filepath=getattr(item, 'filepath', ''),
                        title=item.title or "", artist=getattr(item, 'artist', ''),
                        album=getattr(item, 'album', ''), score=0.9)
                    return result

        # Tier 3: Fuzzy title match (≥ 0.85)
        for item in items:
            it = normalize(item.title or "")
            ratio = difflib.SequenceMatcher(None, nt, it).ratio()
            if ratio > 0.85:
                result.update(
                    status="possible", filepath=getattr(item, 'filepath', ''),
                    title=item.title or "", artist=getattr(item, 'artist', ''),
                    album=getattr(item, 'album', ''), score=round(ratio, 2))
                return result

        # Tier 4: Fuzzy artist match + partial title
        if na:
            for item in items:
                ia = normalize(getattr(item, 'artist', '') or "")
                it = normalize(item.title or "")
                artist_ratio = difflib.SequenceMatcher(None, na, ia).ratio()
                title_ratio = difflib.SequenceMatcher(None, nt, it).ratio()
                if artist_ratio > 0.85 and title_ratio > 0.6:
                    result.update(
                        status="possible", filepath=getattr(item, 'filepath', ''),
                        title=item.title or "", artist=getattr(item, 'artist', ''),
                        album=getattr(item, 'album', ''),
                        score=round(min(artist_ratio, title_ratio), 2))
                    return result

        return result


def match_detected_track(db, title: str, artist: str, album: str = "") -> dict:
    """Legacy compatible wrapper — delegates to RecognitionMatcher."""
    matcher = RecognitionMatcher(db)
    return matcher.match(title, artist, album)


def match_detected_track_simple(title: str, artist: str, items: list) -> dict | None:
    """Simple match against a list of items. Returns first item dict or None."""
    nt = normalize(title)
    na = normalize(artist) if artist else ""
    for item in items:
        it = normalize(getattr(item, 'title', ''))
        ia = normalize(getattr(item, 'artist', '') or "")
        if it == nt and (not na or ia == na):
            return {
                "filepath": item.filepath,
                "title": getattr(item, 'title', ''),
                "artist": getattr(item, 'artist', ''),
                "album": getattr(item, 'album', ''),
            }
    return None
