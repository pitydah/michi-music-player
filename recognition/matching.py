"""Library matching — cross-reference detected tracks with local library."""
import difflib


def normalize(s: str) -> str:
    return " ".join(s.lower().strip().split())


def match_detected_track(db, title: str, artist: str, album: str = "") -> dict:
    """Match a detected track against the library. Returns match dict."""
    result = {"status": "not_found", "filepath": "", "title": "",
              "artist": "", "album": ""}
    if not title:
        return result

    items = db.get_all(search=title) if hasattr(db, 'get_all') else []
    nt = normalize(title)
    na = normalize(artist) if artist else ""

    # 1. Exact title + artist match
    for item in items:
        if normalize(item.title or "") == nt and (not na or normalize(item.artist or "") == na):
            result.update(status="matched", filepath=item.filepath,
                          title=item.title or "", artist=item.artist or "",
                          album=item.album or "")
            return result

    # 2. Title exact + album match
    if album:
        nalbum = normalize(album)
        for item in items:
            if normalize(item.title or "") == nt and normalize(item.album or "") == nalbum:
                result.update(status="matched", filepath=item.filepath,
                              title=item.title or "", artist=item.artist or "",
                              album=item.album or "")
                return result

    # 3. Fuzzy title
    for item in items:
        ratio = difflib.SequenceMatcher(None, nt, normalize(item.title or "")).ratio()
        if ratio > 0.85:
            result.update(status="possible", filepath=item.filepath,
                          title=item.title or "", artist=item.artist or "",
                          album=item.album or "")
            return result

    return result


def match_detected_track_simple(title: str, artist: str, items: list) -> dict | None:
    """Simple match against a list of items. Returns first item dict or None."""
    nt = normalize(title)
    na = normalize(artist) if artist else ""
    for item in items:
        it = normalize(getattr(item, 'title', ''))
        ia = normalize(getattr(item, 'artist', '') or "")
        if it == nt and (not na or ia == na):
            return {"filepath": item.filepath, "title": getattr(item, 'title', ''),
                    "artist": getattr(item, 'artist', ''), "album": getattr(item, 'album', '')}
    return None
