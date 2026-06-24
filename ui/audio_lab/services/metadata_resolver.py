"""Metadata resolver — identifies albums from disc TOC.

Basic implementation present. Full MusicBrainz lookup not yet integrated.
"""

from __future__ import annotations

from ui.audio_lab.models import DiscMetadata


class MetadataResolver:
    def find_album_by_disc_toc(self, toc: dict) -> DiscMetadata | None:
        return None

    def find_album_by_artist_album(self, artist: str, album: str) -> DiscMetadata | None:
        return None

    def merge_metadata_candidates(self, candidates: list[DiscMetadata]) -> DiscMetadata:
        if candidates:
            return candidates[0]
        return DiscMetadata()

    def calculate_confidence(self, candidate: DiscMetadata, disc_info: dict) -> float:
        return 0.0
