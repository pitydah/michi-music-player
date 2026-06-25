"""Metadata normalizer — clean, normalize, and validate extracted tag values."""
import os
import re
import contextlib


# ── Filename-to-metadata inference ──

_SEPARATORS = re.compile(r"\s*[-–—−]\s*|\s*_\s*|\s*\|\s*")
_TRACK_LEAD = re.compile(r"^(\d{1,3})[\s.\-_]*[-–—−]?\s*")


def infer_metadata_from_filename(filepath: str) -> dict[str, str | int]:
    """Infer title, artist, and track_number from a filename.

    Handles patterns like:
        Artist - Title.mp3
        01 - Artist - Title.mp3
        01. Artist - Title.flac
        Artist – Title.mp3
        Artist | Title.mp3
        Artist_Title.mp3
        JustASong.mp3  -> title = JustASong, artist = ""

    Returns dict with keys: title, artist, album, track_number
    """
    stem = os.path.splitext(os.path.basename(str(filepath)))[0].strip()
    result: dict[str, str | int] = {"title": stem, "artist": "", "album": "", "track_number": 0}

    if not stem:
        return result

    # Detect and strip leading track number
    m = _TRACK_LEAD.match(stem)
    if m:
        with contextlib.suppress(ValueError):
            result["track_number"] = int(m.group(1))
        stem = stem[m.end():].strip()

    if not stem:
        return result

    # Try to split on separator
    parts = _SEPARATORS.split(stem, maxsplit=1)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) == 2:
        result["artist"] = parts[0]
        result["title"] = parts[1]
    elif len(parts) == 1:
        result["title"] = parts[0]
    # else: keep title=stem, no artist

    # Clean up redundant whitespace
    result["title"] = " ".join(result["title"].split())
    result["artist"] = " ".join(str(result["artist"]).split())

    return result


def normalize_text(text: str, max_length: int = 256) -> str:
    """Collapse whitespace and truncate."""
    return " ".join(str(text or "").strip().split())[:max_length]


def normalize_artist_name(name: str) -> str:
    """Normalize an artist name for display and grouping."""
    if isinstance(name, (int, float)):
        return ""
    cleaned = re.sub(r"\s+", " ", str(name).strip())
    cleaned = cleaned.strip(";,./\\\"'")
    return cleaned or ""


def normalize_album_title(title: str) -> str:
    """Normalize an album title — case-insensitive grouping key ready."""
    if isinstance(title, (int, float)):
        return "unknown album"
    cleaned = " ".join(str(title).strip().split())
    return cleaned.lower() or "unknown album"


def normalize_genre(text: str) -> str:
    """Normalize genre — strip ID3 parenthetical prefixes like '(123)Rock'."""
    if not text:
        return ""
    cleaned = str(text).strip()
    if cleaned.startswith("(") and ")" in cleaned:
        cleaned = cleaned.split(")", 1)[-1].strip()
    return normalize_text(cleaned, 128)


def normalize_year(value) -> int:
    """Normalize year to int. Handles date strings like '2024-01-15'."""
    if not value:
        return 0
    if isinstance(value, int):
        return value
    with contextlib.suppress(ValueError, TypeError, IndexError):
        s = str(value).strip()
        if s.startswith("(") and ")" in s:
            s = s.split(")", 1)[-1].strip()
        return int(s[:4])
    return 0


def normalize_disc_track(value: str) -> tuple[int, int]:
    """Parse '3/12' or '3' into (number, total)."""
    if not value:
        return 0, 0
    s = str(value).strip()
    with contextlib.suppress(ValueError, TypeError):
        parts = s.split("/")
        num = int(parts[0])
        total = int(parts[1]) if len(parts) > 1 else 0
        return num, total
    return 0, 0


def normalize_bpm(value) -> int:
    """Parse BPM value — handles '128.0', '128', etc."""
    if not value:
        return 0
    with contextlib.suppress(ValueError, TypeError):
        return int(float(str(value).strip()))
    return 0


def normalize_mb_id(value: str) -> str:
    """Normalize a MusicBrainz ID (UUID format)."""
    if not value:
        return ""
    s = str(value).strip()
    s = s.rstrip(":")
    return s if len(s) >= 32 else ""
