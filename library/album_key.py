"""Album keys — stable SHA1 identifiers for artists, albums, and tracks."""
import hashlib


def normalize_key_part(text: str) -> str:
    """Normalize a text part for stable key generation."""
    return " ".join(str(text or "").lower().strip().split())


def make_artist_key(artist_name: str) -> str:
    """Create a stable artist key from a display name."""
    return hashlib.sha1(
        normalize_key_part(artist_name).encode()).hexdigest()[:16]


def make_album_key(albumartist: str, artist: str, album: str) -> str:
    """Create a stable album key.

    Uses albumartist if available, otherwise artist. Falls back to 'unknown'.
    """
    base_artist = normalize_key_part(albumartist or artist or "unknown")
    album_title = normalize_key_part(album or "unknown album")
    raw = f"{base_artist}|{album_title}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def make_track_key(filepath: str, mb_track_id: str = "") -> str:
    """Create a stable track key. Prefers MusicBrainz ID over filepath."""
    if mb_track_id:
        return "mb:" + mb_track_id
    return hashlib.sha1(
        str(filepath).encode()).hexdigest()[:16]
