"""Library enrichment evidence builder (M6.9D).

Builds entity-specific identity evidence from READ-ONLY canonical
library objects plus separately extracted identity hints. Never mutates
canonical models; never merges track-artist and album-artist roles.
"""

from collections.abc import Sequence

from michi.application.enrichment_ports import IdentityHintExtractorPort
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    ExternalIdentityHints,
    LocalAlbumEvidence,
)
from michi.domain.library import AlbumRef, ArtistRef, TrackRef, make_artist_key


def _aggregate_hints(
    extractor: IdentityHintExtractorPort, paths: Sequence
) -> ExternalIdentityHints:
    """Aggregate same-role observations across an album's track files."""
    merged: ExternalIdentityHints | None = None
    for path in paths:
        hints = extractor.extract_hints(path)
        if merged is None:
            merged = hints
            continue
        # R1: AGGREGATION IS A UNION of same-role observations — never
        # `a or b` (which would hide cross-track conflicts).
        merged = ExternalIdentityHints(
            musicbrainz_artist_ids=(
                *merged.musicbrainz_artist_ids,
                *hints.musicbrainz_artist_ids,
            ),
            musicbrainz_album_artist_ids=(
                *merged.musicbrainz_album_artist_ids,
                *hints.musicbrainz_album_artist_ids,
            ),
            musicbrainz_release_group_ids=(
                *merged.musicbrainz_release_group_ids,
                *hints.musicbrainz_release_group_ids,
            ),
            musicbrainz_release_ids=(
                *merged.musicbrainz_release_ids,
                *hints.musicbrainz_release_ids,
            ),
            musicbrainz_recording_ids=(
                *merged.musicbrainz_recording_ids,
                *hints.musicbrainz_recording_ids,
            ),
            musicbrainz_release_track_ids=(
                *merged.musicbrainz_release_track_ids,
                *hints.musicbrainz_release_track_ids,
            ),
        )
    return merged or ExternalIdentityHints()


class LibraryEnrichmentEvidenceBuilder:
    """Read-only canonical-library → identity-evidence projection."""

    def __init__(self, hint_extractor: IdentityHintExtractorPort) -> None:
        self._hint_extractor = hint_extractor

    def artist_evidence(
        self,
        artist: ArtistRef,
        albums: Sequence[AlbumRef],
        tracks: Sequence[TrackRef],
    ) -> ArtistIdentityEvidence:
        """Artist evidence: paired known albums + TRACK-artist-role hints
        from the artist's own track files."""
        known_albums = tuple(
            LocalAlbumEvidence(album.title, album.year)
            for album in albums
            if make_artist_key(album.artist) == artist.key
        )
        artist_paths = [
            track.file_path
            for track in tracks
            if make_artist_key(track.artist) == artist.key
        ]
        raw = _aggregate_hints(self._hint_extractor, artist_paths)
        artist_hints = ArtistIdentityHints.from_file_hints(raw)
        return ArtistIdentityEvidence(
            local_artist_key=artist.key,
            local_artist_name=artist.name,
            known_albums=known_albums,
            identity_hints=artist_hints,
        )

    def album_evidence(
        self,
        album: AlbumRef,
        resolved_artist_external_id: str = "",
    ) -> AlbumIdentityEvidence:
        """Album evidence: title/artist/year + ALBUM-role hints from the
        album's own track files."""
        raw = _aggregate_hints(self._hint_extractor, list(album.track_paths))
        album_hints = AlbumIdentityHints.from_file_hints(raw)
        return AlbumIdentityEvidence(
            local_album_key=album.key,
            local_album_title=album.title,
            local_album_artist_key=make_artist_key(album.artist),
            local_album_artist_name=album.artist,
            resolved_artist_external_id=resolved_artist_external_id,
            local_year=album.year,
            identity_hints=album_hints,
        )
