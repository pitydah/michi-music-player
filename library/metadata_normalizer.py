"""Metadata normalization, validation and catalogue-quality helpers.

The indexer and every batch write use this module as the single normalization
boundary.  Display values keep their human-readable casing while dedicated
``normalized_*`` columns provide deterministic grouping, sorting and filters.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any


# ── Filename-to-metadata inference ──

_SEPARATORS = re.compile(r"\s*[-–—−]\s*|\s*_\s*|\s*\|\s*")
_TRACK_LEAD = re.compile(r"^(\d{1,3})[\s.\-_]*[-–—−]?\s*")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SORT_PUNCTUATION = re.compile(r"[^\w]+", re.UNICODE)
_MB_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_ISRC = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")

_TEXT_LIMITS = {
    "title": 512,
    "artist": 512,
    "album": 512,
    "albumartist": 512,
    "genre": 256,
    "composer": 512,
    "label": 512,
    "conductor": 512,
    "remixer": 512,
    "grouping": 512,
    "mood": 256,
    "comment": 2048,
    "lyricist": 512,
    "copyright": 1024,
    "encoder": 512,
    "media_type": 256,
    "originaldate": 64,
}


def _coerce_scalar(value: Any) -> str:
    """Return a deterministic textual representation of a tag value."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple, set)):
        parts = [_coerce_scalar(item) for item in value]
        return "; ".join(part for part in parts if part)
    return str(value)


def infer_metadata_from_filename(filepath: str) -> dict[str, str | int]:
    """Infer title, artist and track number from a common filename pattern."""
    stem = os.path.splitext(os.path.basename(str(filepath)))[0].strip()
    result: dict[str, str | int] = {
        "title": stem,
        "artist": "",
        "album": "",
        "track_number": 0,
    }
    if not stem:
        return result

    match = _TRACK_LEAD.match(stem)
    if match:
        with contextlib.suppress(ValueError):
            result["track_number"] = int(match.group(1))
        stem = stem[match.end():].strip()

    if not stem:
        return result

    parts = [part.strip() for part in _SEPARATORS.split(stem, maxsplit=1) if part.strip()]
    if len(parts) == 2:
        result["artist"], result["title"] = parts
    elif len(parts) == 1:
        result["title"] = parts[0]

    result["title"] = normalize_text(result["title"])
    result["artist"] = normalize_artist_name(result["artist"])
    return result


# ── Text and identifiers ──


def normalize_text(text: Any, max_length: int = 256) -> str:
    """Normalize Unicode, remove control characters and collapse whitespace."""
    raw = unicodedata.normalize("NFC", _coerce_scalar(text))
    raw = _CONTROL_CHARS.sub(" ", raw)
    return " ".join(raw.strip().split())[:max(0, int(max_length))]


def normalize_sort_text(text: Any, max_length: int = 512) -> str:
    """Build an accent-insensitive, case-folded key for SQL grouping/sorting."""
    display = normalize_text(text, max_length=max_length)
    if not display:
        return ""
    decomposed = unicodedata.normalize("NFKD", display)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    folded = _SORT_PUNCTUATION.sub(" ", without_marks.casefold())
    return " ".join(folded.split())[:max_length]


def normalize_artist_name(name: Any) -> str:
    """Normalize an artist display name without destroying its casing."""
    if isinstance(name, (int, float)):
        return ""
    cleaned = normalize_text(name, 512)
    return cleaned.strip(";,./\\\"'")


def normalize_display_album_title(title: Any) -> str:
    """Normalize an album title for display."""
    if isinstance(title, (int, float)):
        return ""
    return normalize_text(title, 512)


def normalize_album_title(title: Any) -> str:
    """Backward-compatible album grouping key."""
    return normalize_sort_text(title) or "unknown album"


def normalize_genres(value: Any) -> list[str]:
    """Return deduplicated genre values while preserving display casing."""
    raw = normalize_text(value, 1024)
    if not raw:
        return []
    if raw.startswith("(") and ")" in raw:
        raw = raw.split(")", 1)[-1].strip()
    parts = re.split(r"\s*(?:;|\x00|\|)\s*", raw)
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        genre = normalize_text(part, 128)
        key = normalize_sort_text(genre, 128)
        if genre and key not in seen:
            seen.add(key)
            result.append(genre)
    return result


def normalize_genre(text: Any) -> str:
    """Normalize a possibly multi-valued genre tag into a stable display value."""
    return "; ".join(normalize_genres(text))


def normalize_mb_id(value: Any) -> str:
    """Return the first valid MusicBrainz UUID in a scalar or multi-value tag."""
    raw = _coerce_scalar(value).replace("urn:uuid:", "").rstrip(":")
    for candidate in re.split(r"[;,\s]+", raw):
        candidate = candidate.strip().lower()
        if _MB_UUID.fullmatch(candidate):
            return candidate
    return ""


def normalize_isrc(value: Any) -> str:
    """Normalize and validate an International Standard Recording Code."""
    candidate = re.sub(r"[^A-Za-z0-9]", "", _coerce_scalar(value)).upper()
    return candidate if _ISRC.fullmatch(candidate) else ""


# ── Numeric fields ──


def normalize_year(value: Any) -> int:
    """Normalize a release year and reject implausible values."""
    if value in (None, "", 0):
        return 0
    with contextlib.suppress(ValueError, TypeError, IndexError):
        text = _coerce_scalar(value).strip()
        match = re.search(r"(?<!\d)(\d{4})(?!\d)", text)
        year = int(match.group(1) if match else text[:4])
        maximum = datetime.now(timezone.utc).year + 1
        return year if 1000 <= year <= maximum else 0
    return 0


def normalize_disc_track(value: Any) -> tuple[int, int]:
    """Parse ``3/12``, ``3`` or a tuple/list into ``(number, total)``."""
    if value in (None, "", 0):
        return 0, 0
    if isinstance(value, (list, tuple)):
        first = value[0] if value else 0
        second = value[1] if len(value) > 1 else 0
        value = f"{first}/{second}"
    text = _coerce_scalar(value).strip().strip("()")
    text = text.replace(",", "/")
    with contextlib.suppress(ValueError, TypeError):
        parts = text.split("/", 1)
        number = int(float(parts[0])) if parts[0].strip() else 0
        total = int(float(parts[1])) if len(parts) > 1 and parts[1].strip() else 0
        number = number if 0 <= number <= 999 else 0
        total = total if 0 <= total <= 999 else 0
        if total and number > total:
            total = 0
        return number, total
    return 0, 0


def normalize_bpm(value: Any) -> int:
    """Parse a BPM tag, keeping a broad compatibility range."""
    if value in (None, "", 0):
        return 0
    with contextlib.suppress(ValueError, TypeError):
        bpm = int(round(float(_coerce_scalar(value).strip())))
        return bpm if 1 <= bpm <= 999 else 0
    return 0


def _safe_int(value: Any, minimum: int = 0, maximum: int | None = None) -> int:
    with contextlib.suppress(ValueError, TypeError):
        number = int(float(value or 0))
        if number < minimum or (maximum is not None and number > maximum):
            return 0
        return number
    return 0


def _safe_float(value: Any, minimum: float | None = None,
                maximum: float | None = None) -> float:
    with contextlib.suppress(ValueError, TypeError):
        number = float(value or 0.0)
        if minimum is not None and number < minimum:
            return 0.0
        if maximum is not None and number > maximum:
            return 0.0
        return number
    return 0.0


# ── Catalogue health and persistence ──


def assess_metadata_quality(record: dict[str, Any]) -> tuple[int, list[str]]:
    """Return a 0–100 completeness score and machine-readable issue codes."""
    issues: list[str] = []
    score = 0

    weighted_fields = (
        ("title", 28, "missing_title"),
        ("artist", 22, "missing_artist"),
        ("album", 18, "missing_album"),
        ("track_number", 8, "missing_track_number"),
        ("year", 6, "missing_year"),
        ("genre", 5, "missing_genre"),
        ("albumartist", 5, "missing_album_artist"),
    )
    for field, weight, issue in weighted_fields:
        if record.get(field) not in (None, "", 0, 0.0):
            score += weight
        else:
            issues.append(issue)

    if _safe_float(record.get("duration"), minimum=0.001) > 0:
        score += 4
    else:
        issues.append("missing_duration")

    if _safe_int(record.get("sample_rate"), minimum=1) > 0:
        score += 2
    if _safe_int(record.get("channels"), minimum=1) > 0:
        score += 2

    year_value = record.get("year")
    if year_value and not normalize_year(year_value):
        issues.append("invalid_year")
    if record.get("isrc") and not normalize_isrc(record.get("isrc")):
        issues.append("invalid_isrc")

    return min(100, score), issues


def _metadata_source(record: dict[str, Any]) -> str:
    stem = normalize_sort_text(os.path.splitext(record.get("filename", ""))[0])
    title = normalize_sort_text(record.get("title"))
    has_rich_tags = any(record.get(key) for key in (
        "album", "genre", "composer", "mb_track_id", "mb_album_id", "isrc",
    ))
    if has_rich_tags:
        return "embedded_tags"
    if title and title == stem:
        return "filename_inference"
    return "basic_tags" if title or record.get("artist") else "unknown"


def compute_metadata_hash(record: dict[str, Any]) -> str:
    """Hash semantic metadata only, independent of path and file timestamps."""
    fields = (
        "title", "artist", "album", "albumartist", "year", "genre",
        "track_number", "track_total", "disc_number", "disc_total",
        "composer", "isrc", "mb_track_id", "mb_album_id", "mb_artist_id",
        "mb_albumartist_id", "mb_releasegroup_id",
    )
    payload = {field: record.get(field, "") for field in fields}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8", errors="replace")).hexdigest()


def enrich_index_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a BatchWriter record and add searchable metadata diagnostics."""
    result = dict(record)

    for field, limit in _TEXT_LIMITS.items():
        if field in result:
            result[field] = normalize_text(result.get(field), limit)

    result["title"] = normalize_text(result.get("title"), _TEXT_LIMITS["title"])
    result["artist"] = normalize_artist_name(result.get("artist"))
    result["album"] = normalize_display_album_title(result.get("album"))
    result["albumartist"] = normalize_artist_name(result.get("albumartist"))
    result["genre"] = normalize_genre(result.get("genre"))
    result["year"] = normalize_year(result.get("year"))
    result["bpm"] = normalize_bpm(result.get("bpm"))
    result["isrc"] = normalize_isrc(result.get("isrc"))

    track_number, track_total = normalize_disc_track(
        (result.get("track_number", 0), result.get("track_total", 0))
    )
    disc_number, disc_total = normalize_disc_track(
        (result.get("disc_number", 0), result.get("disc_total", 0))
    )
    result["track_number"] = track_number
    result["track_total"] = track_total
    result["disc_number"] = disc_number
    result["disc_total"] = disc_total

    for field in (
        "mb_track_id", "mb_album_id", "mb_albumartist_id", "mb_artist_id",
        "mb_releasegroup_id",
    ):
        result[field] = normalize_mb_id(result.get(field))

    result["normalized_title"] = normalize_sort_text(result.get("title"))
    result["normalized_artist"] = normalize_sort_text(result.get("artist"))
    result["normalized_album"] = normalize_sort_text(result.get("album"))
    result["normalized_albumartist"] = normalize_sort_text(
        result.get("albumartist") or result.get("artist")
    )

    completeness, issues = assess_metadata_quality(result)
    source = _metadata_source(result)
    confidence_base = {
        "embedded_tags": 0.95,
        "basic_tags": 0.80,
        "filename_inference": 0.55,
        "unknown": 0.10,
    }[source]
    result["metadata_source"] = source
    result["metadata_completeness"] = completeness
    result["metadata_confidence"] = round(
        min(1.0, confidence_base * (0.65 + completeness / 285.0)), 4
    )
    result["metadata_issues"] = json.dumps(issues, ensure_ascii=False, separators=(",", ":"))
    result["metadata_hash"] = compute_metadata_hash(result)
    return result
