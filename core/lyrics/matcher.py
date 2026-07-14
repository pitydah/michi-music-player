from __future__ import annotations

from core.lyrics.models import (
    TrackIdentity, LyricsDocument, MatchConfidence,
)
from core.lyrics.normalizer import TrackIdentityNormalizer


def compute_match_score(identity: TrackIdentity, candidate: LyricsDocument) -> MatchConfidence:
    normalizer = TrackIdentityNormalizer()
    norm_query = normalizer.normalize(identity)

    cand_title = candidate.metadata.title or ""
    cand_artist = candidate.metadata.artist or ""
    cand_album = candidate.metadata.album or ""

    norm_candidate = normalizer.normalize(TrackIdentity(
        title=cand_title, artist=cand_artist, album=cand_album,
    ))

    score = 0.0

    title_score = _score_field(norm_query.normalized_title, norm_candidate.normalized_title)
    score += title_score * 40.0

    artist_score = _score_field(norm_query.normalized_artist, norm_candidate.normalized_artist)
    score += artist_score * 35.0

    album_score = _score_field(norm_query.normalized_album, norm_candidate.normalized_album)
    score += album_score * 15.0

    if identity.duration_ms > 0 and candidate.duration_ms > 0:
        ratio = abs(identity.duration_ms - candidate.duration_ms) / max(identity.duration_ms, 1)
        if ratio < 0.05:
            score += 10.0
        elif ratio > 0.3:
            score -= 20.0

    if identity.musicbrainz_track_id and candidate.identity.musicbrainz_track_id and identity.musicbrainz_track_id == candidate.identity.musicbrainz_track_id:
        score += 50.0

    if identity.isrc and candidate.identity.isrc and identity.isrc == candidate.identity.isrc:
        score += 30.0

    query_live = normalizer.is_live_version(identity.title)
    cand_live = normalizer.is_live_version(cand_title)
    if query_live != cand_live:
        score -= 15.0

    query_remix = normalizer.is_remix(identity.title)
    cand_remix = normalizer.is_remix(cand_title)
    if query_remix != cand_remix:
        score -= 10.0

    if score >= 75:
        return MatchConfidence.EXACT
    elif score >= 55:
        return MatchConfidence.HIGH_CONFIDENCE
    elif score >= 35:
        return MatchConfidence.AMBIGUOUS
    elif score >= 15:
        return MatchConfidence.LOW_CONFIDENCE
    return MatchConfidence.REJECTED


def _score_field(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    if query == candidate:
        return 1.0
    if query in candidate or candidate in query:
        return 0.8
    q_words = set(query.split())
    c_words = set(candidate.split())
    if not q_words or not c_words:
        return 0.0
    intersection = q_words & c_words
    union = q_words | c_words
    jaccard = len(intersection) / len(union)
    return jaccard


def rank_candidates(identity: TrackIdentity, candidates: list[LyricsDocument]) -> list[tuple[LyricsDocument, MatchConfidence]]:
    scored = []
    for c in candidates:
        conf = compute_match_score(identity, c)
        if conf != MatchConfidence.REJECTED:
            scored.append((c, conf))
    scored.sort(key=lambda x: _confidence_order(x[1]), reverse=True)
    return scored


def _confidence_order(conf: MatchConfidence) -> int:
    order = {
        MatchConfidence.EXACT: 100,
        MatchConfidence.HIGH_CONFIDENCE: 80,
        MatchConfidence.AMBIGUOUS: 60,
        MatchConfidence.LOW_CONFIDENCE: 40,
        MatchConfidence.REJECTED: 0,
        MatchConfidence.UNKNOWN: 10,
    }
    return order.get(conf, 0)
