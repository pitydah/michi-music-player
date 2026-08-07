"""MixService must return explicit generation statuses (ADR-005 / criterion 50):
an empty outcome is never presented as a generated mix, and ok=True is only
valid for COMPLETED_WITH_TRACKS / PARTIAL_RECOMMENDATION.
"""
from __future__ import annotations

from core.assistant_gateways import ProductionMixGateway
from core.library.library_query_service import LibraryQueryService
from core.mix_service import MixService
from library.library_db import LibraryDB
from recommendation.smart_mix_service import SmartMixService

TRACKS = [
    ("/m/jazz-one.flac", "jazz-one.flac", "/m", ".flac", "Jazz One",
     "Miles Davis", "Kind of Blue", 1959, "Jazz", 370, 900, "uid-j1"),
    ("/m/jazz-two.flac", "jazz-two.flac", "/m", ".flac", "Jazz Two",
     "John Coltrane", "A Love Supreme", 1965, "Jazz", 480, 900, "uid-j2"),
    ("/m/rock-one.flac", "rock-one.flac", "/m", ".flac", "Rock One",
     "Led Zeppelin", "IV", 1971, "Rock", 420, 1000, "uid-r1"),
]


def _make_db(tracks: list | None = None) -> LibraryDB:
    db = LibraryDB(":memory:")
    if tracks:
        db.conn.executemany(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title, artist, album, "
            "year, genre, duration, bitrate, track_uid) "
            "VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?, ?, ?, ?)",
            tracks,
        )
    db.conn.commit()
    return db


def _stack(db: LibraryDB) -> MixService:
    return MixService(
        db=db,
        smart_mix_service=SmartMixService(db=db),
        library_query_service=LibraryQueryService(db=db),
    )


class TestExplicitStatuses:
    def test_valid_strategy_with_matches_is_completed(self):
        svc = _stack(_make_db(TRACKS))
        result = svc.generate("lossless_showcase", limit=10)

        assert result["ok"] is True
        assert result["status"] == "COMPLETED_WITH_TRACKS"
        assert len(result["tracks"]) > 0
        first = result["tracks"][0]
        assert first["id"] and first["title"]
        assert "explanation" in first, "explanations must be surfaced"
        assert first["explanation"]["reason_summary"]

    def test_library_with_tracks_but_no_matches_is_no_matches(self):
        svc = _stack(_make_db(TRACKS))
        result = svc.generate("decade_mix", seed={"year": "1990"}, limit=10)

        assert result["ok"] is False
        assert result["status"] == "NO_MATCHES", result
        assert result["tracks"] == []
        assert "coincide" in result["message"].lower()

    def test_recent_without_history_is_no_matches(self):
        svc = _stack(_make_db(TRACKS))
        result = svc.generate("recent", limit=10)

        assert result["ok"] is False
        assert result["status"] == "NO_MATCHES", result

    def test_empty_library_is_empty_library(self):
        svc = _stack(_make_db())
        result = svc.generate("daily", limit=10)

        assert result["ok"] is False
        assert result["status"] == "EMPTY_LIBRARY", result
        assert result["tracks"] == []

    def test_unknown_strategy_is_invalid_strategy(self):
        svc = _stack(_make_db(TRACKS))
        result = svc.generate("nuclear_launch", limit=10)

        assert result["ok"] is False
        assert result["status"] == "INVALID_STRATEGY", result

    def test_missing_generator_is_generator_unavailable(self):
        svc = MixService(db=_make_db(TRACKS), smart_mix_service=None,
                         library_query_service=None)
        result = svc.generate("daily", limit=10)

        assert result["ok"] is False
        assert result["status"] == "GENERATOR_UNAVAILABLE", result

    def test_partial_recommendation_when_seed_track_missing(self):
        db = _make_db(TRACKS)
        svc = _stack(db)
        result = svc.generate(
            "similar_to_artist",
            seed={"track_id": 999999, "artist": "Miles Davis"},
            limit=10,
        )

        assert result["ok"] is True
        assert result["status"] == "PARTIAL_RECOMMENDATION", result
        assert result["tracks"], "partial results still carry tracks"
        assert result["warnings"], "partial reasons must be reported"


class TestGatewayMapping:
    def test_gateway_maps_empty_library_to_no_matches(self):
        db = _make_db()
        svc = _stack(db)
        gateway = ProductionMixGateway(svc)
        result = gateway.create_mix("daily")

        assert result["ok"] is False
        assert result["code"] == "NO_MATCHES", result
        assert result["status"] == "EMPTY_LIBRARY"

    def test_gateway_maps_no_matches_honestly(self):
        db = _make_db(TRACKS)
        svc = _stack(db)
        gateway = ProductionMixGateway(svc)
        result = gateway.create_mix("decade_mix", year="1990")

        assert result["ok"] is False
        assert result["code"] == "NO_MATCHES", result

    def test_gateway_surfaces_completed_with_tracks(self):
        db = _make_db(TRACKS)
        svc = _stack(db)
        gateway = ProductionMixGateway(svc)
        result = gateway.create_mix("lossless_showcase", limit=10)

        assert result["ok"] is True
        assert result["tracks"], result
