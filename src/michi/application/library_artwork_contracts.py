"""Library-specific artwork observation/cache contracts.

Kept separate from application/ports.py because the latter contains
frozen cross-subsystem contracts (M11.3F hash gate).

These contracts model R4 artwork truth:

    FOUND
    ABSENT_CONFIRMED
    UNAVAILABLE

UNAVAILABLE means "do not destroy last-known cache" — an observation that
could not be completed is NOT evidence of absence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from michi.domain.library import Artwork


class ArtworkProbeVerdict(StrEnum):
    FOUND = "found"
    ABSENT_CONFIRMED = "absent_confirmed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ArtworkProbeObservation:
    verdict: ArtworkProbeVerdict
    artwork: Artwork | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.verdict is ArtworkProbeVerdict.FOUND:
            if self.artwork is None:
                raise ValueError("FOUND artwork observation requires artwork")
        elif self.artwork is not None:
            raise ValueError("non-FOUND artwork observation cannot carry artwork")

    @classmethod
    def found(cls, artwork: Artwork) -> ArtworkProbeObservation:
        return cls(verdict=ArtworkProbeVerdict.FOUND, artwork=artwork)

    @classmethod
    def absent(cls) -> ArtworkProbeObservation:
        return cls(verdict=ArtworkProbeVerdict.ABSENT_CONFIRMED)

    @classmethod
    def unavailable(cls, detail: str = "") -> ArtworkProbeObservation:
        return cls(verdict=ArtworkProbeVerdict.UNAVAILABLE, detail=detail)


@dataclass(frozen=True)
class PreparedArtwork:
    album_key: str
    filename: str
    path: Path


class AlbumArtworkProbePort(Protocol):
    def probe_album_artwork(
        self,
        track_paths: tuple[Path, ...],
        token=None,
    ) -> ArtworkProbeObservation: ...


class PreparedArtworkCachePort(Protocol):
    def prepare_artwork(
        self,
        album_key: str,
        artwork: Artwork,
    ) -> PreparedArtwork | None: ...

    def commit_manifest_batch(
        self,
        *,
        upserts: tuple[PreparedArtwork, ...],
        removals: tuple[str, ...],
    ) -> dict[str, Path]: ...
