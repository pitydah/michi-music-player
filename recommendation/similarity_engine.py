"""Similarity engine — local, rule-based, explainable music recommendations."""

from __future__ import annotations

import random
from typing import Any

from recommendation.schemas import RecommendationResult, SeedCriteria


def _get(item, attr, default=""):
    val = getattr(item, attr, None)
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return val
    return str(val).strip()


def _same_artist(a, b) -> bool:
    return _get(a, "artist").lower() == _get(b, "artist").lower()


def _genre_overlap(a, b) -> float:
    ga = set(_get(a, "genre").lower().replace(",", " ").replace("/", " ").split())
    gb = set(_get(b, "genre").lower().replace(",", " ").replace("/", " ").split())
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / max(len(ga | gb), 1)


def _year_proximity(a, b) -> float:
    ya = _get(a, "year")
    yb = _get(b, "year")
    try:
        ya_int = int(ya) if ya else 0
        yb_int = int(yb) if yb else 0
    except (ValueError, TypeError):
        return 0.0
    if not ya_int or not yb_int:
        return 0.0
    diff = abs(ya_int - yb_int)
    return 1.0 / (1.0 + diff * 0.2)


def _format_match(a, b) -> int:
    return int(_get(a, "ext").lower() == _get(b, "ext").lower())


def _quality_bonus(item) -> float:
    ext = _get(item, "ext").lower()
    if ext in ("flac", "wav", "aiff", "dsf", "dff"):
        return 1.0
    bitrate = _get(item, "bitrate")
    try:
        if int(bitrate) >= 900:
            return 0.8
        if int(bitrate) >= 320:
            return 0.5
    except (ValueError, TypeError):
        pass
    return 0.0


def _build_result(item, score: float, reasons: list[str],
                  strategy: str) -> RecommendationResult:
    return RecommendationResult(
        track_id=_get(item, "id"),
        title=_get(item, "title"),
        artist=_get(item, "artist"),
        album=_get(item, "album"),
        year=int(_get(item, "year") or 0),
        genre=_get(item, "genre"),
        duration=float(_get(item, "duration") or 0),
        format=str(_get(item, "ext")).lstrip("."),
        score=round(score, 4),
        reasons=reasons,
        strategy=strategy,
    )


def metadata_similarity(all_items: list, seed: Any, limit: int = 30,
                        exclude_id: int = 0) -> list[RecommendationResult]:
    results: list[RecommendationResult] = []
    for item in all_items:
        if exclude_id and _get(item, "id") == exclude_id:
            continue
        artist_match = 1.0 if _same_artist(item, seed) else (
            0.5 if _get(seed, "artist").lower() in _get(item, "albumartist").lower() else 0.0
        )
        genre_match = _genre_overlap(item, seed)
        year_prox = _year_proximity(item, seed)
        fmt_match = _format_match(item, seed) * 0.1
        quality = _quality_bonus(item)

        score = (
            artist_match * 0.30
            + genre_match * 0.30
            + year_prox * 0.15
            + fmt_match * 0.10
            + quality * 0.15
        )

        if score < 0.05:
            continue

        reasons = []
        if artist_match >= 1.0:
            reasons.append("Mismo artista")
        elif artist_match >= 0.5:
            reasons.append("Artista relacionado")
        if genre_match >= 0.5:
            reasons.append(f"Genero similar a {_get(seed, 'genre')}")
        if year_prox >= 0.8:
            reasons.append(f"Ano cercano: {_get(seed, 'year')}")
        if quality >= 0.8:
            reasons.append("Alta calidad de audio")

        results.append(_build_result(item, score, reasons, "metadata_similarity"))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]


def discovery(all_items: list, played_ids: set[int] = None,
              profile_top_genres: list[str] = None,
              profile_top_artists: list[str] = None,
              limit: int = 30) -> list[RecommendationResult]:
    played_ids = played_ids or set()
    profile_top_genres = [g.lower() for g in (profile_top_genres or [])]
    profile_top_artists = [a.lower() for a in (profile_top_artists or [])]

    results: list[RecommendationResult] = []
    for item in all_items:
        tid = _get(item, "id")
        never_played = tid not in played_ids if played_ids else 1.0
        genre_match = 0.0
        item_genre = _get(item, "genre").lower()
        for g in profile_top_genres:
            if g in item_genre:
                genre_match = max(genre_match, 0.8)
        artist_novelty = 0.0
        item_artist = _get(item, "artist").lower()
        if item_artist not in profile_top_artists:
            artist_novelty = 0.5
        quality = _quality_bonus(item)

        score = (
            never_played * 0.40
            + genre_match * 0.30
            + artist_novelty * 0.20
            + quality * 0.10
        )

        if score < 0.05:
            continue

        reasons = []
        if never_played:
            reasons.append("No la has escuchado")
        if genre_match >= 0.8:
            reasons.append("Genero que te gusta")
        if artist_novelty >= 0.5:
            reasons.append("Artista nuevo para ti")

        results.append(_build_result(item, score, reasons, "discovery"))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]


def favorites_like(all_items: list, favorite_ids: set[int],
                   limit: int = 30) -> list[RecommendationResult]:
    favorites = [i for i in all_items if _get(i, "id") in favorite_ids]
    if not favorites:
        return []
    avg: dict[str, Any] = {}
    for item in favorites:
        for attr in ("artist", "genre", "year", "ext"):
            val = _get(item, attr)
            if val:
                avg.setdefault(attr, []).append(val)

    seed = SeedCriteria(
        artist=max(set(avg.get("artist", [])), key=avg.get("artist", []).count) if avg.get("artist") else "",
        genre=max(set(avg.get("genre", [])), key=avg.get("genre", []).count) if avg.get("genre") else "",
        year=int(sum(int(y) for y in avg.get("year", []) if y) / max(len(avg.get("year", [])), 1)) if avg.get("year") else 0,
        ext=max(set(avg.get("ext", [])), key=avg.get("ext", []).count) if avg.get("ext") else "",
    )

    return metadata_similarity(all_items, seed, limit)


def seed_radio(all_items: list, seed: Any, limit: int = 30,
               exclude_id: int = 0) -> list[RecommendationResult]:
    direct = metadata_similarity(all_items, seed, limit=10, exclude_id=exclude_id)

    same_album = [
        i for i in all_items
        if _same_artist(i, seed) and _get(i, "album") == _get(seed, "album")
        and _get(i, "id") != exclude_id
    ]
    same_artist_other = [
        i for i in all_items
        if _same_artist(i, seed) and _get(i, "album") != _get(seed, "album")
        and _get(i, "id") != exclude_id
    ]
    same_genre_diff_artist = [
        i for i in all_items
        if _genre_overlap(i, seed) >= 0.5 and not _same_artist(i, seed)
        and _get(i, "id") != exclude_id
    ]

    results: list[RecommendationResult] = []
    results.extend(direct)

    for item in same_album[:5]:
        results.append(_build_result(item, 0.75, ["Mismo album"], "seed_radio"))
    for item in same_artist_other[:5]:
        results.append(_build_result(item, 0.70, ["Mismo artista, otro album"], "seed_radio"))
    for item in same_genre_diff_artist[:5]:
        results.append(_build_result(item, 0.60, ["Mismo genero", "Descubrimiento"], "seed_radio"))

    seen = set()
    deduped = []
    for r in results:
        if r.track_id not in seen:
            seen.add(r.track_id)
            deduped.append(r)

    return deduped[:limit]


def balanced_mix(all_items: list, seed: Any, limit: int = 30) -> list[RecommendationResult]:
    familiar = metadata_similarity(all_items, seed, limit=limit // 2)
    disc = discovery(all_items, limit=limit - len(familiar))
    results: list[RecommendationResult] = []
    for i in range(max(len(familiar), len(disc))):
        if i < len(familiar):
            results.append(familiar[i])
        if i < len(disc):
            results.append(disc[i])
    return results[:limit]


def quality_mix(all_items: list, limit: int = 30) -> list[RecommendationResult]:
    high_quality = [i for i in all_items if _quality_bonus(i) >= 0.5]
    random.shuffle(high_quality)
    results: list[RecommendationResult] = []
    for item in high_quality[:limit]:
        results.append(_build_result(
            item, _quality_bonus(item),
            ["Alta calidad de audio", str(_get(item, "ext")).upper()],
            "quality_mix",
        ))
    return results


def acoustic_similarity(all_items: list, seed: Any,
                        analysis_svc: Any = None,
                        limit: int = 30) -> list[RecommendationResult]:
    results: list[RecommendationResult] = []
    if analysis_svc is None:
        return results

    seed_id = _get(seed, "id")
    if not seed_id:
        return results

    similar = analysis_svc.find_sonically_similar(int(seed_id), limit=limit) if hasattr(analysis_svc, "find_sonically_similar") else []
    for s in similar:
        for item in all_items:
            if _get(item, "id") == s.get("track_id"):
                results.append(_build_result(
                    item, s.get("score", 0.5),
                    s.get("reasons", ["Similitud acustica"]),
                    "acoustic_similarity",
                ))
                break
    return results[:limit]


def hybrid_score(track: Any, seed: Any, profile: Any = None,
                 acoustic_weight: float = 0.0,
                 analysis_svc: Any = None) -> tuple[float, list[str]]:
    metadata_score = 0.0
    artist_match = 1.0 if _get(track, "artist").lower() == _get(seed, "artist").lower() else 0.0
    genre_match = _genre_overlap(track, seed)
    year_prox = _year_proximity(track, seed)
    metadata_score = (
        artist_match * 0.30
        + genre_match * 0.30
        + year_prox * 0.15
        + _format_match(track, seed) * 0.10
        + _quality_bonus(track) * 0.15
    )

    profile_score = 0.0
    if profile:
        if _get(track, "artist").lower() in [a.lower() for a in (profile.top_artists or [])]:
            profile_score += 0.6
        if _get(track, "genre").lower() in [g.lower() for g in (profile.top_genres or [])]:
            profile_score += 0.4
        profile_score = min(profile_score, 1.0)

    acoustic_score = 0.0
    acoustic_reasons: list[str] = []
    if acoustic_weight > 0 and analysis_svc:
        from audio_analysis.feature_extractor import make_track_key
        seed_fp = getattr(seed, "filepath", "")
        cand_key = make_track_key(getattr(track, "filepath", ""))
        if seed_fp and analysis_svc.has_features(make_track_key(seed_fp)):
            safe = analysis_svc.get_safe_labels(cand_key) if analysis_svc.has_features(cand_key) else None
            if safe and safe.get("acoustic_labels") != ["no_data"]:
                acoustic_reasons = safe.get("acoustic_labels", [])
                acoustic_score = 0.5

    if acoustic_weight > 0:
        total = (
            metadata_score * (1.0 - acoustic_weight) * 0.55
            + profile_score * (1.0 - acoustic_weight) * 0.35
            + acoustic_score * acoustic_weight
            + (0.10 if not hasattr(track, "_seen") else 0.0)
        )
    else:
        total = metadata_score * 0.55 + profile_score * 0.35 + _quality_bonus(track) * 0.10

    reasons = []
    if artist_match:
        reasons.append("Mismo artista")
    if genre_match >= 0.5:
        reasons.append("Genero similar")
    if year_prox >= 0.8:
        reasons.append("Ano cercano")
    reasons.extend(acoustic_reasons)

    return (round(min(total, 1.0), 4), reasons)
