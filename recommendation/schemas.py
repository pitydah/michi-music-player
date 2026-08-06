"""Schemas for the recommendation engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class RecommendationResult:
    track_id: int = 0
    title: str = ""
    artist: str = ""
    album: str = ""
    year: int = 0
    genre: str = ""
    duration: float = 0.0
    format: str = ""
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    strategy: str = ""


@dataclass
class RecommendationExplanation:
    track_id: int = 0
    score: float = 0.0
    reason_summary: str = ""
    detailed_reasons: list[str] = field(default_factory=list)


@dataclass
class TrackSignal:
    track_key: str = ""
    signal_type: str = ""
    signal_value: float = 1.0
    source: str = ""
    timestamp: str = ""


@dataclass
class ListeningProfile:
    top_artists: list[str] = field(default_factory=list)
    top_genres: list[str] = field(default_factory=list)
    top_albums: list[str] = field(default_factory=list)
    preferred_years: list[int] = field(default_factory=list)
    preferred_formats: list[str] = field(default_factory=list)
    skipped_genres: list[str] = field(default_factory=list)
    unplayed_count: int = 0
    favorite_count: int = 0
    total_plays: int = 0
    recent_artist: str = ""
    recent_genre: str = ""
    updated_at: str = ""


@dataclass
class SeedCriteria:
    """Static seed criteria for similarity engines (replaces dynamic classes).

    The similarity functions only read attributes (``artist``, ``genre``,
    ``year``, ``ext``, ``album``), so a plain dataclass is a drop-in
    replacement for the former ``type("Seed", ...)`` construction.
    """

    artist: str = ""
    genre: str = ""
    year: int = 0
    ext: str = ""
    album: str = ""


@dataclass
class SmartMix:
    mix_id: str = ""
    title: str = ""
    description: str = ""
    strategy: str = ""
    seed_type: str = ""
    seed_value: str = ""
    tracks: list[RecommendationResult] = field(default_factory=list)
    explanation: str = ""
    created_at: str = ""
    is_saved: bool = False
    warnings: list[str] = field(default_factory=list)


def generate_mix_id() -> str:
    return f"mix_{uuid.uuid4().hex[:10]}"


def generate_recommendation_id() -> str:
    return f"rec_{uuid.uuid4().hex[:10]}"
