"""Playlist domain model (LOCAL-06)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Playlist:
    """A user-defined persistent ordered collection of track paths."""

    name: str
    track_paths: tuple[str, ...] = ()
