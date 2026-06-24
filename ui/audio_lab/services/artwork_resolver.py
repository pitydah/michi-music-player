"""Artwork resolver — album cover search and download.

Network search not yet implemented. Local cover embedding deferred to TagWriter.
"""

from __future__ import annotations


class ArtworkResolver:
    def search_album_art(self, album_metadata: dict) -> list[dict]:
        return []

    def rank_artwork_quality(self, results: list[dict]) -> list[dict]:
        return results

    def download_cover(self, url: str, destination: str):
        pass

    def embed_cover(self, audio_file: str, cover_file: str):
        pass

    def save_cover_file(self, cover_file: str, album_folder: str):
        pass
