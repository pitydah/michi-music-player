"""Album identity — robust normalization and canonical key generation.

Provides utilities for normalizing album titles and artist names,
detecting compilation albums, and building stable AlbumIdentity objects.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass


_EDITION_TOKENS = [
    r"remaster(?:ed)?", r"deluxe\s+edition", r"expanded\s+edition",
    r"anniversary\s+edition", r"bonus\s+tracks?", r"special\s+edition",
]
_EDITION_PATTERNS = [
    re.compile(r"[-–—\s]*\(?" + tok + r"\)?[-–—\s]*", re.IGNORECASE)
    for tok in _EDITION_TOKENS
]
_STRIP_PATTERN = re.compile(r"[\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
_QUOTES_PATTERN = re.compile(r"[\u2018\u2019\u201a\u201b']")
_DQUOTES_PATTERN = re.compile(r"[\u201c\u201d\u201e\u201f\u00ab\u00bb]")


def _fold(text: str) -> str:
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = _QUOTES_PATTERN.sub("'", s)
    s = _DQUOTES_PATTERN.sub('"', s)
    s = s.strip().lower()
    s = _STRIP_PATTERN.sub(" ", s)
    return s


def normalize_album_title(text: str, strip_edition: bool = False) -> str:
    """Normalize an album title for comparison.

    If strip_edition is True, removes edition suffixes for fuzzy matching.
    """
    s = _fold(text)
    if strip_edition:
        for pat in _EDITION_PATTERNS:
            s = pat.sub("", s)
        s = _STRIP_PATTERN.sub(" ", s).strip()
    return s


_VA_ALIASES = frozenset({
    "va", "v.a.", "v a", "varios artistas", "various", "various artists",
})


def is_various_artist_alias(text: str) -> bool:
    """Check if a string is an alias for 'Various Artists'."""
    s = _fold(text) if text else ""
    return s in _VA_ALIASES


def normalize_artist_name(text: str) -> str:
    """Normalize an artist name for comparison.

    Returns folded lowercase string, or empty string for empty/None input.
    Does NOT automatically convert empty to 'various artists'.
    """
    s = _fold(text) if text else ""
    return s


def detect_album_artist(tracks: list) -> str:
    """Detect the definitive album artist from a list of tracks.

    Priority:
      1. albumartist if consistent across tracks
      2. most common artist
      3. Various Artists
    """
    if not tracks:
        return "Artista desconocido"

    aa_candidates = {}
    artist_candidates = {}
    for t in tracks:
        aa = str(getattr(t, "albumartist", "") or "").strip()
        ar = str(getattr(t, "artist", "") or "").strip()
        if aa:
            aak = normalize_artist_name(aa)
            aa_candidates[aak] = aa_candidates.get(aak, 0) + 1
        if ar:
            ark = normalize_artist_name(ar)
            artist_candidates[ark] = artist_candidates.get(ark, 0) + 1

    if aa_candidates:
        best_aa_key = max(aa_candidates, key=aa_candidates.get)
        best_aa_count = aa_candidates[best_aa_key]
        total_aa = sum(aa_candidates.values())
        if not is_various_artist_alias(best_aa_key) and best_aa_count > total_aa // 2:
            return _find_original(tracks, "albumartist", best_aa_key,
                                  default="Various Artists")

    if artist_candidates:
        best_ar_key = max(artist_candidates, key=artist_candidates.get)
        best_ar_count = artist_candidates[best_ar_key]
        total_ar = sum(artist_candidates.values())
        if len(artist_candidates) > 1 and best_ar_count <= total_ar // 2:
            return "Various Artists"
        if not is_various_artist_alias(best_ar_key):
            return _find_original(tracks, "artist", best_ar_key,
                                  default="Artista desconocido")
        if len(artist_candidates) <= 1:
            return _find_original(tracks, "artist", best_ar_key,
                                  default="Artista desconocido")

    return "Various Artists"


def _find_original(tracks: list, attr: str, norm_key: str, default: str) -> str:
    for t in tracks:
        val = str(getattr(t, attr, "") or "").strip()
        if normalize_artist_name(val) == norm_key and val:
            return val
    return default


def make_canonical_album_identity(tracks: list) -> str:
    """Build a stable canonical album key from tracks.

    Uses albumartist + album title. Falls back to artist + album title.
    Considers compilation and edition markers.
    """
    artist = detect_album_artist(tracks)
    title = str(getattr(tracks[0], "album", "") or "Álbum desconocido") if tracks else ""
    norm_artist = normalize_artist_name(artist)
    norm_title = normalize_album_title(title)
    raw = f"{norm_artist}|{norm_title}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def is_compilation(tracks: list) -> bool:
    """Detect if a list of tracks represents a compilation album.

    Only returns True if:
      - albumartist is explicitly set to a VA alias, OR
      - any track has a truthy 'compilation' attribute
    Multiple different artists WITHOUT an albumartist marker is NOT treated as
    compilation (they will be split into separate artist groups instead).
    """
    if not tracks:
        return False
    albumartists = {str(getattr(t, "albumartist", "") or "").strip()
                    for t in tracks if str(getattr(t, "albumartist", "") or "").strip()}
    if any(is_various_artist_alias(aa) for aa in albumartists):
        return True
    if any(getattr(t, "compilation", False) for t in tracks):
        return True
    return False


@dataclass(frozen=True)
class AlbumIdentity:
    album_key: str = ""
    canonical_title: str = ""
    canonical_artist: str = ""
    display_title: str = ""
    display_artist: str = ""
    year: str = ""
    is_compilation: bool = False
    disc_count: int = 1
    confidence: float = 1.0


def compute_album_identity(tracks: list) -> AlbumIdentity:
    """Compute a complete AlbumIdentity from a list of tracks."""
    if not tracks:
        return AlbumIdentity()
    title = str(getattr(tracks[0], "album", "") or "Álbum desconocido")
    artist = detect_album_artist(tracks)
    year = str(getattr(tracks[0], "year", "") or "")
    canon_title = normalize_album_title(title)
    canon_artist = normalize_artist_name(artist)
    key = make_canonical_album_identity(tracks)

    discs = {getattr(t, "disc_number", 0) or 1 for t in tracks}

    return AlbumIdentity(
        album_key=key,
        canonical_title=canon_title,
        canonical_artist=canon_artist,
        display_title=title,
        display_artist=artist,
        year=year,
        is_compilation=is_compilation(tracks),
        disc_count=max(discs),
    )
