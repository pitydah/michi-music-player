"""Album duplicate detection — find potential duplicates without auto-merging."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from library.album_identity import normalize_album_title, normalize_artist_name
from library.album_repository import AlbumGroup

logger = logging.getLogger("michi.album_duplicate")


@dataclass
class AlbumDuplicateCandidate:
    left_key: str = ""
    right_key: str = ""
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    recommended_action: str = "review"  # review | manual | safe


class AlbumDuplicateService:
    """Detects potential duplicate albums without merging automatically."""

    def find_duplicates(self, groups: list[AlbumGroup]) -> list[AlbumDuplicateCandidate]:
        """Scan all album groups for potential duplicates."""
        candidates = []
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                g1 = groups[i]
                g2 = groups[j]
                candidate = self._compare(g1, g2)
                if candidate.confidence >= 0.6:
                    candidates.append(candidate)
        return candidates

    def find_for_group(self, groups: list[AlbumGroup],
                       target: AlbumGroup) -> list[AlbumDuplicateCandidate]:
        """Find duplicates for a specific album group."""
        candidates = []
        for g in groups:
            if g.identity.album_key == target.identity.album_key:
                continue
            candidate = self._compare(target, g)
            if candidate.confidence >= 0.6:
                candidates.append(candidate)
        return candidates

    def _compare(self, g1: AlbumGroup, g2: AlbumGroup) -> AlbumDuplicateCandidate:
        """Compare two AlbumGroup entries and compute duplicate confidence."""
        id1 = g1.identity
        id2 = g2.identity
        score = 0.0
        reasons = []

        title1 = normalize_album_title(id1.display_title)
        title2 = normalize_album_title(id2.display_title)
        art1 = normalize_artist_name(id1.display_artist)
        art2 = normalize_artist_name(id2.display_artist)

        if title1 == title2 and art1 == art2:
            score += 0.5
            reasons.append("Mismo título y artista")

        stripped1 = normalize_album_title(id1.display_title, strip_edition=True)
        stripped2 = normalize_album_title(id2.display_title, strip_edition=True)
        if stripped1 == stripped2 and title1 != title2:
            score += 0.2
            reasons.append("Mismo título sin edición/remaster")

        if id1.year and id2.year and id1.year == id2.year:
            score += 0.1
            reasons.append("Mismo año")

        t1 = len(g1.tracks)
        t2 = len(g2.tracks)
        if t1 == t2:
            score += 0.1
        elif abs(t1 - t2) <= 2:
            score += 0.05

        if g1.quality and g2.quality and \
           g1.quality.dominant_format != g2.quality.dominant_format:
                score += 0.05
                reasons.append(f"Formato distinto: {g1.quality.dominant_format} vs {g2.quality.dominant_format}")

        if score >= 0.95:
            action = "safe"
        elif score >= 0.8:
            action = "review"
        else:
            action = "manual"

        return AlbumDuplicateCandidate(
            left_key=id1.album_key,
            right_key=id2.album_key,
            confidence=min(score, 1.0),
            reasons=reasons,
            recommended_action=action,
        )
