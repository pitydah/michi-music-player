"""Mix domain models — canonical result states for mix generation.

``MixGenerationStatus`` is the source of truth for what a mix generation
actually produced.  ``ok=True`` in a mix result is only valid for
``COMPLETED_WITH_TRACKS`` (and ``PARTIAL_RECOMMENDATION``, which still
returns tracks); an empty outcome is never presented as a generated mix
(ADR-005).
"""
from __future__ import annotations

from enum import Enum


class MixGenerationStatus(str, Enum):
    COMPLETED_WITH_TRACKS = "COMPLETED_WITH_TRACKS"
    NO_MATCHES = "NO_MATCHES"
    EMPTY_LIBRARY = "EMPTY_LIBRARY"
    INVALID_STRATEGY = "INVALID_STRATEGY"
    GENERATOR_UNAVAILABLE = "GENERATOR_UNAVAILABLE"
    PARTIAL_RECOMMENDATION = "PARTIAL_RECOMMENDATION"


# Strategies the MixService facade can dispatch.  Smart strategies are
# handled by SmartMixService ("recent" is a library-history strategy);
# query-backed categories (the QML mix hub ids) are handled by
# MixQueryService through MixService — the bridge never dispatches them.
KNOWN_STRATEGIES = frozenset({
    "daily", "balanced", "recent", "genre_journey", "decade_mix",
    "lossless_showcase", "favorites_neighbors", "recently_missed",
    "deep_cuts", "similar_to_artist", "similar_to_album",
    # QML mix categories — single facade for every strategy.
    "favorites", "most_played", "unplayed", "rediscovery", "daily_mix",
    "by_artist", "by_genre", "by_album", "by_decade", "by_year",
    "high_quality", "custom",
})
