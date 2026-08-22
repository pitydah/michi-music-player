"""READ-ONLY external identity-hint extraction (M6.9D).

A SEPARATE enrichment-specific extractor — the canonical
``InfrastructureMetadataExtractor`` is untouched and must never read
MusicBrainz tags. Hints are LOCAL EVIDENCE (context 2), never canonical
metadata, and tag bytes are NEVER written.

Unreadable/corrupt tag blocks yield EMPTY hints (never an error for the
library scan — most libraries contain no MBIDs).
"""

import logging

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.enrichment_ports import IdentityHintExtractorPort
from michi.domain.enrichment import ExternalIdentityHints, dedupe_identity_ids

logger = logging.getLogger(__name__)

# tag key (casefolded) -> ExternalIdentityHints semantic role
_ARTIST_ROLE_KEYS = {"musicbrainz_artistid": "artist_ids"}
_ALBUM_ARTIST_ROLE_KEYS = {"musicbrainz_albumartistid": "album_artist_ids"}
_ALBUM_ROLE_KEYS = {
    "musicbrainz_releasegroupid": "release_group_ids",
    "musicbrainz_albumid": "release_ids",
}
_OTHER_ROLE_KEYS = {
    "musicbrainz_recordingid": "recording_ids",
    "musicbrainz_releasetrackid": "release_track_ids",
}

_ALL_ROLES = {
    **_ARTIST_ROLE_KEYS,
    **_ALBUM_ARTIST_ROLE_KEYS,
    **_ALBUM_ROLE_KEYS,
    **_OTHER_ROLE_KEYS,
}


def _as_strings(value) -> list[str]:
    """Accept str / list[str] observations only; never coerce numbers."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, str)]
    return []


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

        observed: dict[str, list[str]] = {}
        for key, value in audio.tags.items():
            role = _ALL_ROLES.get(str(key).casefold())
            if role is None:
                continue
            observed.setdefault(role, []).extend(_as_strings(value))

        def single(role: str) -> str:
            """First distinct non-blank observation for a single-value
            role (extra distinct observations ride the tuple roles; the
            domain conflict gates remain authoritative)."""
            ids = dedupe_identity_ids(observed.get(role, []))
            return ids[0] if ids else ""

        return ExternalIdentityHints(
            musicbrainz_artist_ids=dedupe_identity_ids(observed.get("artist_ids", [])),
            musicbrainz_album_artist_ids=dedupe_identity_ids(
                observed.get("album_artist_ids", [])
            ),
            musicbrainz_release_group_id=single("release_group_ids"),
            musicbrainz_release_id=single("release_ids"),
            musicbrainz_recording_id=single("recording_ids"),
            musicbrainz_release_track_id=single("release_track_ids"),
        )
