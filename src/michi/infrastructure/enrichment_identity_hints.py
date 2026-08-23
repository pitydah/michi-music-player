"""READ-ONLY external identity-hint extraction (M6.9D + BACKEND-R1.1).

A SEPARATE enrichment-specific extractor — the canonical
``InfrastructureMetadataExtractor`` is untouched and must never read
MusicBrainz tags. Hints are LOCAL EVIDENCE (context 2), never canonical
metadata, and tag bytes are NEVER written.

R1.1 REAL-MUTAGEN FAMILY SUPPORT (verified against mutagen 1.47):

- Vorbis family (FLAC / Ogg / Opus):
    keys MUSICBRAINZ_ARTISTID, MUSICBRAINZ_ALBUMARTISTID,
    MUSICBRAINZ_RELEASEGROUPID, MUSICBRAINZ_ALBUMID,
    MUSICBRAINZ_RECORDINGID, MUSICBRAINZ_TRACKID,
    MUSICBRAINZ_RELEASETRACKID (str values).
- ID3 (MP3 / WAV):
    TXXX frames keyed ``TXXX:<desc>`` with case-insensitive
    "MusicBrainz ..." descriptions (str values); the RECORDING id rides
    a UFID frame with owner "http://musicbrainz.org" (bytes data) — the
    real Picard representation.
- MP4/M4A:
    freeform atoms ``----:com.apple.iTunes:MusicBrainz ...`` whose
    values are bytes (MP4FreeForm is a bytes subclass).
- ASF/WMA:
    ``MusicBrainz/...`` keys with str values.
- Anything unreadable or with unrecognized representations yields
  EMPTY hints — never an error for the library scan.

Every role keeps ALL distinct observations (strip, drop blanks, dedupe
identical) — never first-wins; conflicts belong to the domain gates.
"""

import logging

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.enrichment_ports import IdentityHintExtractorPort
from michi.domain.enrichment import ExternalIdentityHints, dedupe_identity_ids

logger = logging.getLogger(__name__)

# role -> set of recognized key spellings (casefolded)
_ROLE_KEYS: dict[str, set[str]] = {
    "artist_ids": {
        "musicbrainz_artistid",
        "musicbrainz/artist id",
        "musicbrainz artist id",
    },
    "album_artist_ids": {
        "musicbrainz_albumartistid",
        "musicbrainz/album artist id",
        "musicbrainz album artist id",
    },
    "release_group_ids": {
        "musicbrainz_releasegroupid",
        "musicbrainz/release group id",
        "musicbrainz release group id",
    },
    "release_ids": {
        "musicbrainz_albumid",
        "musicbrainz/album id",
        "musicbrainz album id",
    },
    "recording_ids": {
        "musicbrainz_recordingid",
        "musicbrainz_trackid",  # real Picard/Vorbis key (R1.2)
        "musicbrainz/track id",
        "musicbrainz track id",
    },
    "release_track_ids": {
        "musicbrainz_releasetrackid",
        "musicbrainz/release track id",
        "musicbrainz release track id",
    },
}

_ROLE_BY_KEY: dict[str, str] = {
    spelling: role for role, spellings in _ROLE_KEYS.items() for spelling in spellings
}

_MB_UFID_OWNER = "http://musicbrainz.org"


def _role_for_key(key: str) -> str | None:
    """Family-agnostic role mapping: bare spellings (Vorbis/ASF) plus
    the MP4 freeform prefix stripped (----:com.apple.itunes:...)."""
    normalized = key.casefold().strip()
    role = _ROLE_BY_KEY.get(normalized)
    if role is not None:
        return role
    for prefix in ("----:com.apple.itunes:", "----:com.apple.iTunes:"):
        if normalized.startswith(prefix.casefold()):
            return _ROLE_BY_KEY.get(normalized[len(prefix.casefold()) :])
    return None


_SENTINEL = object()


def _extract_text_value(value) -> list[str]:
    """R1.2 STRICT recursive extraction.

    Accepts ONLY str / bytes (valid UTF-8) / lists+tuples of those /
    Mutagen attribute objects exposing a ``.value`` that is str or
    bytes. NO generic str(...) coercion — arbitrary representations are
    never fabricated into identity values.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        try:
            return [value.decode("utf-8")]
        except UnicodeDecodeError:
            return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            result.extend(_extract_text_value(item))
        return result
    raw = getattr(value, "value", _SENTINEL)
    if raw is _SENTINEL:
        return []
    return _extract_text_value(raw)


def _as_strings(value) -> list[str]:
    """Public helper kept for compatibility; delegates to the strict
    recursive extractor (ASF attribute objects included)."""
    return _extract_text_value(value)


class MutagenIdentityHintExtractor(IdentityHintExtractorPort):
    """Extracts MusicBrainz/Picard identity tags from local files."""

    def extract_hints(self, file_path) -> ExternalIdentityHints:
        try:
            audio = MutagenFile(str(file_path), easy=False)
        except (OSError, MutagenError) as exc:
            logger.debug("identity hints unreadable for %s: %s", file_path, exc)
            return ExternalIdentityHints()
        if audio is None or audio.tags is None:
            return ExternalIdentityHints()
        return self.extract_hints_from_tags(audio.tags)

    def extract_hints_from_tags(self, tags) -> ExternalIdentityHints:
        """R1.1 seam over REAL mutagen tag objects (all families).

        Iterates ``tags.items()`` exactly like the file path does and
        applies the family-agnostic role mapping + full same-role
        observation preservation."""
        observed: dict[str, list[str]] = {}
        for raw_key, value in tags.items():
            key = str(raw_key)
            role = _role_for_key(key)
            if role is not None:
                observed.setdefault(role, []).extend(_as_strings(value))
                continue
            # ID3 TXXX frames: key "TXXX:<desc>" — desc drives the role.
            if key.casefold().startswith("txxx:"):
                role = _role_for_key(key[5:])
                if role is not None:
                    desc_attr = getattr(value, "text", None)
                    observed.setdefault(role, []).extend(_as_strings(desc_attr))
                continue
            # ID3 UFID frames: recording id via the MusicBrainz owner.
            if key.casefold().startswith("ufid:"):
                owner = key[5:].strip()
                if owner.casefold() == _MB_UFID_OWNER:
                    observed.setdefault("recording_ids", []).extend(
                        _as_strings(getattr(value, "data", None))
                    )
                continue
            # Fallback: any other key whose casefolded form matches a
            # known role spelling (Vorbis/ASF variants already covered,
            # defensive for unknown tag families).
        return ExternalIdentityHints(
            musicbrainz_artist_ids=dedupe_identity_ids(observed.get("artist_ids", [])),
            musicbrainz_album_artist_ids=dedupe_identity_ids(
                observed.get("album_artist_ids", [])
            ),
            musicbrainz_release_group_ids=dedupe_identity_ids(
                observed.get("release_group_ids", [])
            ),
            musicbrainz_release_ids=dedupe_identity_ids(
                observed.get("release_ids", [])
            ),
            musicbrainz_recording_ids=dedupe_identity_ids(
                observed.get("recording_ids", [])
            ),
            musicbrainz_release_track_ids=dedupe_identity_ids(
                observed.get("release_track_ids", [])
            ),
        )
