"""Tag writer — reads and writes metadata tags to audio files.

CURRENTLY A STUB. Real implementation pending in feat/audio-lab-tag-writer.
"""

from __future__ import annotations


class TagWriter:
    """Tag metadata reader/writer. NOT YET IMPLEMENTED."""

    @property
    def available(self) -> bool:
        return False

    def read_tags(self, path: str) -> dict:
        return {}

    def write_tags(self, path: str, metadata: dict):
        """Not yet implemented."""

    def write_batch(self, paths: list[str], metadata: dict):
        """Not yet implemented."""

    def embed_cover(self, path: str, cover_path: str):
        """Not yet implemented."""
