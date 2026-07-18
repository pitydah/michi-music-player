"""Metadata matcher — compare local metadata with KnowledgeBroker candidates."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from metadata.review.schemas import MetadataFieldChange

_STRIP_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "replace").decode("ascii")
    s = s.lower().strip()
    s = _STRIP_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s)
    return s.strip()


def _exact_match(a: str, b: str) -> bool:
    return _normalize(a) == _normalize(b)


def _fuzzy_match(a: str, b: str) -> bool:
    na = _normalize(a)
    nb = _normalize(b)
    if na == nb:
        return True
    return bool(na and nb and (na in nb or nb in na))


def _mbid_match(a: str, b: str) -> bool:
    return bool(a and b and a.strip().lower() == b.strip().lower())


def compare_artist(local: dict[str, Any],
                   kb_artist: dict[str, Any]) -> list[MetadataFieldChange]:
    changes: list[MetadataFieldChange] = []
    kb_name = kb_artist.get("name", "")
    kb_mbid = kb_artist.get("mbid", "")

    local_name = str(local.get("artist", "") or "")
    local_albumartist = str(local.get("albumartist", "") or "")
    local_mbid = str(local.get("mb_albumartist_id", "") or local.get("mb_track_id", "") or "")

    if _mbid_match(local_mbid, kb_mbid):
        confidence = 1.0
        reason = "MBID coincide"
    elif _exact_match(local_name, kb_name):
        confidence = 0.95
        reason = "Nombre de artista coincide exacto"
    elif _fuzzy_match(local_name, kb_name):
        confidence = 0.82
        reason = "Nombre de artista coincide parcialmente"
    else:
        return changes

    if local_name and _exact_match(local_name, kb_name):
        pass  # already matches

    if not local_name and kb_name and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="artist", current_value=local_name,
            suggested_value=kb_name, source="musicbrainz",
            confidence=confidence, reason=reason,
        ))

    if not local_albumartist and kb_name and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="albumartist", current_value=local_albumartist,
            suggested_value=kb_name, source="musicbrainz",
            confidence=confidence, reason="Artista de album igual al artista",
        ))

    if local_mbid and not _mbid_match(local_mbid, kb_mbid) and kb_mbid:
        changes.append(MetadataFieldChange(
            field="mb_albumartist_id", current_value=local_mbid,
            suggested_value=kb_mbid, source="musicbrainz",
            confidence=0.85, reason="MBID actualizado desde MusicBrainz",
        ))
    elif not local_mbid and kb_mbid and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="mb_albumartist_id", current_value="",
            suggested_value=kb_mbid, source="musicbrainz",
            confidence=confidence, reason="MBID nuevo desde MusicBrainz",
        ))

    return changes


def compare_album(local: dict[str, Any],
                  kb_album: dict[str, Any]) -> list[MetadataFieldChange]:
    changes: list[MetadataFieldChange] = []
    kb_title = kb_album.get("title", "")
    kb_year = kb_album.get("year", "")
    kb_cover = kb_album.get("cover_url", "")
    kb_mbid = kb_album.get("release_group_mbid", "")
    kb_artist = kb_album.get("artist_name", "")

    local_title = str(local.get("album", "") or "")
    local_year = str(local.get("year", "") or "")
    local_mbid = str(local.get("mb_album_id", "") or "")
    local_artist = str(local.get("artist", "") or "")

    artist_match = _exact_match(local_artist, kb_artist) or _fuzzy_match(local_artist, kb_artist)
    if _mbid_match(local_mbid, kb_mbid):
        confidence = 1.0
        reason = "MBID de album coincide"
    elif _exact_match(local_title, kb_title) and artist_match:
        confidence = 0.95
        reason = "Titulo de album y artista coinciden exacto"
    elif _fuzzy_match(local_title, kb_title) and artist_match:
        confidence = 0.85
        reason = "Titulo de album similar con mismo artista"
    elif _fuzzy_match(local_title, kb_title):
        confidence = 0.70
        reason = "Titulo de album similar (artista no verificado)"
    else:
        return changes

    if not local_title and kb_title and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="album", current_value=local_title,
            suggested_value=kb_title, source="musicbrainz",
            confidence=confidence, reason=reason,
        ))

    if kb_year and (not local_year or local_year != kb_year):
        try:
            lyr = int(local_year) if local_year else 0
            kyr = int(kb_year) if kb_year else 0
            if not lyr or abs(lyr - kyr) <= 1:
                if not lyr:
                    changes.append(MetadataFieldChange(
                        field="year", current_value=local_year,
                        suggested_value=kb_year, source="musicbrainz",
                        confidence=confidence, reason="Año desde release-group",
                    ))
                elif lyr != kyr:
                    changes.append(MetadataFieldChange(
                        field="year", current_value=local_year,
                        suggested_value=kb_year, source="musicbrainz",
                        confidence=0.70, reason="Año difiere por 1 año",
                    ))
        except ValueError:
            pass

    if not local_mbid and kb_mbid and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="mb_album_id", current_value="",
            suggested_value=kb_mbid, source="musicbrainz",
            confidence=confidence, reason="MBID de album desde MusicBrainz",
        ))

    if not local.get("cover_url") and kb_cover and confidence >= 0.80:
        changes.append(MetadataFieldChange(
            field="cover_url", current_value="",
            suggested_value=kb_cover, source="coverart",
            confidence=0.85, reason="Portada desde Cover Art Archive",
        ))

    return changes


def compare_track(local: dict[str, Any],
                  kb_recording: dict[str, Any]) -> list[MetadataFieldChange]:
    changes: list[MetadataFieldChange] = []
    kb_title = kb_recording.get("title", "")
    kb_isrc = kb_recording.get("isrc", "")
    kb_mbid = kb_recording.get("recording_mbid", "")
    kb_length = kb_recording.get("length_ms", 0)

    local_title = str(local.get("title", "") or "")
    local_isrc = str(local.get("isrc", "") or "")
    local_duration = float(local.get("duration", 0) or 0) * 1000

    title_match = _exact_match(local_title, kb_title)
    isrc_match = _mbid_match(local_isrc, kb_isrc)
    duration_close = abs(local_duration - kb_length) < 5000 if kb_length and local_duration else False

    if isrc_match:
        confidence = 1.0
        reason = "ISRC coincide"
    elif title_match and duration_close:
        confidence = 0.95
        reason = "Titulo y duracion coinciden"
    elif title_match:
        confidence = 0.90
        reason = "Titulo coincide"
    elif _fuzzy_match(local_title, kb_title):
        confidence = 0.70
    else:
        return changes

    if not local_isrc and kb_isrc and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="isrc", current_value="",
            suggested_value=kb_isrc, source="musicbrainz",
            confidence=confidence, reason=reason,
        ))

    if not local.get("mb_track_id") and kb_mbid and confidence >= 0.75:
        changes.append(MetadataFieldChange(
            field="mb_track_id", current_value="",
            suggested_value=kb_mbid, source="musicbrainz",
            confidence=confidence, reason=reason,
        ))

    return changes
