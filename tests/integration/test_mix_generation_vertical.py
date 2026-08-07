"""Vertical slice: real MixService + real DB tracks → honest mix outcome.

ProductionMixGateway.generate_mix must reach MixService and return either a
real mix with tracks or an honest NO_MATCHES — never CAPABILITY_UNAVAILABLE
and never a fake success (ok=True with zero content).
"""
from __future__ import annotations

from core.assistant_initializer import create_assistant_composition
from core.library.library_query_service import LibraryQueryService
from core.mix_service import MixService
from core.playlist_service import PlaylistService
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


def _make_db() -> LibraryDB:
    db = LibraryDB(":memory:")
    db.conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "year, genre, duration, bitrate, track_uid) "
        "VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?, ?, ?, ?)",
        TRACKS,
    )
    db.conn.commit()
    return db


def _stack():
    db = _make_db()
    query_service = LibraryQueryService(db=db)
    smart_mix = SmartMixService(db=db)
    mix_service = MixService(
        db=db,
        smart_mix_service=smart_mix,
        library_query_service=query_service,
    )
    playlist_service = PlaylistService(db=db)
    comp = create_assistant_composition(
        library_db=db,
        library_query_service=query_service,
        mix_service=mix_service,
        playlist_service=playlist_service,
    )
    return db, mix_service, comp, playlist_service


def test_mix_generation_reaches_real_service() -> None:
    _db, mix_service, comp, _pl = _stack()

    result = comp.tool_registry.execute(
        "create_smart_mix", {"strategy": "daily", "limit": 10}
    )

    assert result.ok is True, f"mix generation failed: {result.error}"
    assert result.data.get("ok") is True
    assert result.data.get("code") != "CAPABILITY_UNAVAILABLE"
    tracks = result.data.get("tracks") or []
    assert len(tracks) > 0, "mix reported ok but returned zero tracks (fake success)"


def test_mix_capability_is_available_with_real_service() -> None:
    _db, _mix_service, comp, _pl = _stack()
    caps = comp.capability_resolver.resolve("mix.generate")
    assert caps["mix.generate"].available is True


def test_mix_gateway_surfaces_no_matches_honestly() -> None:
    db = LibraryDB(":memory:")
    db.conn.commit()
    query_service = LibraryQueryService(db=db)
    mix_service = MixService(
        db=db,
        smart_mix_service=SmartMixService(db=db),
        library_query_service=query_service,
    )
    from core.assistant_gateways import ProductionMixGateway

    gateway = ProductionMixGateway(mix_service)
    result = gateway.create_mix("daily")

    assert result["code"] != "CAPABILITY_UNAVAILABLE"
    if result.get("ok"):
        assert result.get("tracks"), "ok=True but no tracks"
    else:
        assert result.get("code") in ("NO_MATCHES", "MIX_FAILED",
                                      "SERVICE_UNAVAILABLE"), result


def test_save_last_mix_as_playlist() -> None:
    db, mix_service, comp, playlist_service = _stack()
    gateway = comp.gateways.mix
    mix = gateway.create_mix("daily", limit=10)
    assert mix["ok"], mix

    saved = gateway.save_mix_as_playlist(mix["mix_id"], "Mix Guardado")

    assert saved["ok"] is True, saved
    assert playlist_service.list(), "playlist was not persisted"
