"""AlbumRepository — unified source for album data from MediaItem lists.

Provides: album grouping, identity, summary, quality, health, duplicate detection.
Pure Python — no Qt dependencies.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from library.album_identity import (
    AlbumIdentity, compute_album_identity, make_canonical_album_identity,
    normalize_album_title, normalize_artist_name,
    is_compilation,
)
from metadata.album_summary import AlbumSummary

logger = logging.getLogger("michi.album_repository")


@dataclass
class AlbumTrackView:
    """Public view of a track within an album, safe for serialization."""
    filepath: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    track_number: int = 0
    disc_number: int = 1
    duration: float = 0.0
    year: int = 0
    genre: str = ""
    ext: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    quality_label: str = ""
    quality_kind: str = "unknown"

    def exists(self) -> bool:
        import os
        return os.path.isfile(self.filepath)

    @classmethod
    def from_media_item(cls, item) -> AlbumTrackView:
        return cls(
            filepath=str(getattr(item, "filepath", "") or ""),
            title=str(getattr(item, "title", "") or getattr(item, "filename", "") or ""),
            artist=str(getattr(item, "artist", "") or ""),
            album=str(getattr(item, "album", "") or ""),
            albumartist=str(getattr(item, "albumartist", "") or ""),
            track_number=int(getattr(item, "track_number", 0) or 0),
            disc_number=int(getattr(item, "disc_number", 0) or 1),
            duration=float(getattr(item, "duration", 0) or 0),
            year=int(getattr(item, "year", 0) or 0),
            genre=str(getattr(item, "genre", "") or ""),
            ext=str(getattr(item, "ext", "") or "").lstrip(".").upper(),
            bitrate=int(getattr(item, "bitrate", 0) or 0),
            sample_rate=int(getattr(item, "sample_rate", 0) or 0),
        )


@dataclass
class AlbumQualitySummary:
    dominant_format: str = ""
    formats: list[str] = field(default_factory=list)
    dominant_quality: str = "unknown"
    dominant_sample_rate: int = 0
    dominant_bit_depth: int = 0
    average_bitrate: int = 0
    has_mixed_quality: bool = False
    has_hires: bool = False
    has_lossless: bool = False
    has_lossy: bool = False
    has_dsd: bool = False
    replaygain_tracks: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class AlbumHealthSummary:
    track_count: int = 0
    disc_count: int = 1
    total_duration: float = 0.0
    missing_files: int = 0
    missing_titles: int = 0
    missing_artists: int = 0
    missing_albumartist: int = 0
    missing_genres: int = 0
    missing_years: int = 0
    missing_cover: bool = False
    possible_duplicate: bool = False
    status: str = "ok"  # ok | warning | danger

    def __post_init__(self):
        if self.status == "ok" and self._has_issues():
            self.status = "warning"

    def _has_issues(self) -> bool:
        return any([
            self.track_count <= 0,
            self.missing_files > 0,
            self.missing_titles > 0,
            self.missing_artists > 0,
            self.missing_albumartist > 0,
            self.missing_genres > 0,
            self.missing_years > 0,
            self.missing_cover,
            self.possible_duplicate,
        ])


@dataclass
class AlbumGroup:
    identity: AlbumIdentity = None
    tracks: list = field(default_factory=list)
    summary: AlbumSummary | None = None
    quality: AlbumQualitySummary | None = None
    health: AlbumHealthSummary | None = None
    cover_path: str = ""

    def __post_init__(self):
        if self.identity is None:
            self.identity = AlbumIdentity()


class AlbumRepository:
    """Unified source for album data built from a MediaItem list."""

    def __init__(self):
        self._groups: dict[str, AlbumGroup] = {}
        self._built = False

    def build(self, items: list) -> None:
        """Build album groups from a list of MediaItem-like objects."""
        self._groups = {}

        # First pass: group by album title
        by_title: dict[str, list] = {}
        for item in items:
            album = normalize_album_title(str(getattr(item, "album", "") or ""))
            if album not in by_title:
                by_title[album] = []
            by_title[album].append(item)

        # Second pass: within each title group, further split by canonical identity
        merged: dict[str, list] = {}
        for _, title_group in by_title.items():
            # Compute identity for the full title group
            comp = is_compilation(title_group)
            if comp:
                # Compilation — single group if albumartist is Various Artists
                key = make_canonical_album_identity(title_group)
                merged[key] = title_group
            else:
                # Split by individual normalized artist
                artist_subs: dict[str, list] = {}
                for item in title_group:
                    ar = normalize_artist_name(
                        str(getattr(item, "albumartist", "") or "") or
                        str(getattr(item, "artist", "") or ""))
                    if ar not in artist_subs:
                        artist_subs[ar] = []
                    artist_subs[ar].append(item)
                for sub_list in artist_subs.values():
                    key = make_canonical_album_identity(sub_list)
                    if key not in merged:
                        merged[key] = []
                    merged[key].extend(sub_list)

        for key, track_list in merged.items():
            identity = compute_album_identity(track_list)
            summary = self._build_summary(track_list, identity)
            quality = self._build_quality(track_list)
            health = self._build_health(track_list, summary)
            group = AlbumGroup(
                identity=identity,
                tracks=track_list,
                summary=summary,
                quality=quality,
                health=health,
            )
            self._groups[key] = group

        self._built = True

    def list_groups(self) -> list[AlbumGroup]:
        return list(self._groups.values())

    def get_group(self, album_key: str) -> AlbumGroup | None:
        return self._groups.get(album_key)

    def get_tracks(self, album_key: str) -> list:
        g = self._groups.get(album_key)
        return g.tracks if g else []

    def get_summary(self, album_key: str) -> AlbumSummary | None:
        g = self._groups.get(album_key)
        return g.summary if g else None

    def get_quality_summary(self, album_key: str) -> AlbumQualitySummary:
        g = self._groups.get(album_key)
        return g.quality if g and g.quality else AlbumQualitySummary()

    def get_health_summary(self, album_key: str) -> AlbumHealthSummary:
        g = self._groups.get(album_key)
        return g.health if g and g.health else AlbumHealthSummary()

    def find_duplicate_candidates(self) -> list:
        """Find potential duplicate album groups."""
        self.list_groups()
        candidates = []
        keys = list(self._groups.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                g1 = self._groups[keys[i]]
                g2 = self._groups[keys[j]]
                score = self._duplicate_score(g1, g2)
                if score >= 0.6:
                    candidates.append((g1, g2, score))
        return candidates

    def invalidate(self, album_key: str = "") -> None:
        if album_key:
            self._groups.pop(album_key, None)
        else:
            self._groups = {}
            self._built = False

    def _build_quality(self, tracks: list) -> AlbumQualitySummary:
        formats = {}
        sample_rates = {}
        bit_depths = {}
        total_bitrate = 0
        has_dsd = False

        for t in tracks:
            ext = str(getattr(t, "ext", "") or "").lstrip(".").upper()
            formats[ext] = formats.get(ext, 0) + 1
            sr = int(getattr(t, "sample_rate", 0) or 0)
            bd = int(getattr(t, "bit_depth", 0) or 0)
            br = int(getattr(t, "bitrate", 0) or 0)
            if sr:
                sample_rates[sr] = sample_rates.get(sr, 0) + 1
            if bd:
                bit_depths[bd] = bit_depths.get(bd, 0) + 1
            if br:
                total_bitrate += br

            has_dsd = has_dsd or ext in ("DSF", "DFF", "DSD")

        dominant_fmt = max(formats, key=formats.get) if formats else ""
        total = len(tracks)

        has_lossless = any(e in ("FLAC", "ALAC", "WAV", "AIFF") for e in formats)
        has_lossy = any(e in ("MP3", "AAC", "OGG", "OPUS") for e in formats)
        has_mixed = has_lossless and has_lossy
        has_hires = any(sr > 48000 for sr in sample_rates)

        dominant_sr = max(sample_rates, key=sample_rates.get) if sample_rates else 0
        dominant_bd = max(bit_depths, key=bit_depths.get) if bit_depths else 0
        avg_br = total_bitrate // total if total and total_bitrate else 0

        quality = "lossless" if has_lossless else "lossy" if has_lossy else "unknown"
        if has_dsd:
            quality = "dsd"
        elif has_hires and has_lossless:
            quality = "hires"

        warnings = []
        if has_mixed:
            warnings.append("Calidad mixta (lossless + lossy)")
        if has_dsd:
            warnings.append("Audio DSD detectado")

        return AlbumQualitySummary(
            dominant_format=dominant_fmt,
            formats=list(formats.keys()),
            dominant_quality=quality,
            dominant_sample_rate=dominant_sr,
            dominant_bit_depth=dominant_bd,
            average_bitrate=avg_br,
            has_mixed_quality=has_mixed,
            has_hires=has_hires,
            has_lossless=has_lossless,
            has_lossy=has_lossy,
            has_dsd=has_dsd,
            warnings=warnings,
        )

    def _build_health(self, tracks: list, summary: AlbumSummary) -> AlbumHealthSummary:
        import os
        mf = sum(1 for t in tracks if not os.path.isfile(
            str(getattr(t, "filepath", "") or "")))
        mt = sum(1 for t in tracks if not str(
            getattr(t, "title", "") or getattr(t, "filename", "") or "").strip())
        mar = sum(1 for t in tracks if not str(
            getattr(t, "artist", "") or "").strip())
        maa = sum(1 for t in tracks if not str(
            getattr(t, "albumartist", "") or "").strip())
        mg = sum(1 for t in tracks if not str(
            getattr(t, "genre", "") or "").strip())
        myr = sum(1 for t in tracks if not int(
            getattr(t, "year", 0) or 0))

        discs = {getattr(t, "disc_number", 0) or 1 for t in tracks}
        total_dur = sum(float(getattr(t, "duration", 0) or 0) for t in tracks)

        return AlbumHealthSummary(
            track_count=len(tracks),
            disc_count=max(discs),
            total_duration=total_dur,
            missing_files=mf,
            missing_titles=mt,
            missing_artists=mar,
            missing_albumartist=maa,
            missing_genres=mg,
            missing_years=myr,
        )

    def _duplicate_score(self, g1: AlbumGroup, g2: AlbumGroup) -> float:
        """Compare two album groups and return a duplicate confidence score."""
        id1 = g1.identity
        id2 = g2.identity
        score = 0.0

        if id1.canonical_title == id2.canonical_title:
            score += 0.4
            if id1.canonical_artist == id2.canonical_artist:
                score += 0.3
        else:
            nt1 = normalize_album_title(id1.display_title, strip_edition=True)
            nt2 = normalize_album_title(id2.display_title, strip_edition=True)
            if nt1 == nt2:
                score += 0.25
                if id1.canonical_artist == id2.canonical_artist:
                    score += 0.25

        if id1.year and id1.year == id2.year:
            score += 0.1

        if len(g1.tracks) == len(g2.tracks):
            score += 0.1
        elif abs(len(g1.tracks) - len(g2.tracks)) <= 2:
            score += 0.05

        return min(score, 1.0)

    def _build_summary(self, tracks: list, identity: AlbumIdentity) -> AlbumSummary:
        return AlbumSummary(
            album_key=identity.album_key,
            title=identity.display_title,
            artist=identity.display_artist,
            year=identity.year,
            track_count=len(tracks),
        )

def album_groups_to_cover_items(groups: list, cover_size: int = 200) -> list:
    return []



