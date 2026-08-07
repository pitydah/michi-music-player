"""Search domains live in SearchRequest, never in the query text (Slice 6).

The service treats the query as literal text; only the QML bridge parses
``track:``/``album:`` style intent and converts it into a domains set.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_service_source_never_parses_prefixes() -> None:
    source = (PROJECT_ROOT / "core" / "global_search_service.py").read_text(
        encoding="utf-8"
    )
    providers = (PROJECT_ROOT / "core" / "search" / "providers.py").read_text(
        encoding="utf-8"
    )
    for haystack, name in ((source, "global_search_service.py"),
                           (providers, "core/search/providers.py")):
        assert '"track:"' not in haystack, f"{name} must not parse track: prefixes"
        assert '"album:"' not in haystack, f"{name} must not parse album: prefixes"
        assert '"artist:"' not in haystack, f"{name} must not parse artist: prefixes"
        assert "startswith(" not in haystack, f"{name} must not split query prefixes"


def test_bridge_is_the_only_prefix_parser() -> None:
    bridge = (PROJECT_ROOT / "ui_qml_bridge" / "global_search_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "DOMAIN_MAP" in bridge, "Bridge owns the domain-key mapping"


def test_query_with_prefix_is_treated_as_literal_text() -> None:
    """Searching 'track:A' with domains={TRACK} searches the literal text
    'track:A'; a track titled 'A' is NOT found, proving the service does not
    strip/interpret the prefix."""
    from core.global_search_service import GlobalSearchService
    from core.search.models import SearchDomain, SearchRequest
    from core.search.providers import SearchProviderRegistry, TrackSearchRepository

    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT, title TEXT, artist TEXT, album TEXT,
            album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            year INTEGER DEFAULT 0, deleted_at TEXT, albumartist TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
            title, artist, album, albumartist, content=media_items,
            content_rowid=id
        )
    """)
    conn.execute(
        "INSERT INTO media_items (filepath, title, artist, album, album_key) "
        "VALUES (?, ?, ?, ?, ?)",
        ("/x.flac", "A", "Band", "Album", "k1"),
    )
    conn.commit()
    conn.execute(
        "INSERT INTO media_fts (rowid, title, artist, album) "
        "SELECT id, title, artist, album FROM media_items"
    )
    conn.commit()
    conn.close()
    try:
        registry = SearchProviderRegistry()
        registry.register(SearchDomain.TRACK, TrackSearchRepository(path))
        svc = GlobalSearchService(db_path=path, provider_registry=registry)
        clean = svc.search_request(SearchRequest(
            query="A", domains=frozenset({SearchDomain.TRACK}), request_id="1"))
        assert any(i.result_type == "track" and i.title == "A"
                   for i in clean.items), "clean query must find the track"
        prefixed = svc.search_request(SearchRequest(
            query="track:A", domains=frozenset({SearchDomain.TRACK}),
            request_id="2"))
        assert all(i.result_type != "track" or i.title != "A"
                   for i in prefixed.items), (
            "'track:A' must be searched as literal text, not remapped"
        )
        assert "TRACK" in prefixed.status_codes
    finally:
        os.unlink(path)


def test_domains_come_only_from_search_request() -> None:
    """The same literal query returns different domains per SearchRequest."""
    from core.global_search_service import GlobalSearchService
    from core.search.models import SearchDomain, SearchRequest

    svc = GlobalSearchService(db_path="")
    track_only = svc.search_request(SearchRequest(
        query="x", domains=frozenset({SearchDomain.TRACK}), request_id="1"))
    album_only = svc.search_request(SearchRequest(
        query="x", domains=frozenset({SearchDomain.ALBUM}), request_id="2"))
    assert "TRACK" in track_only.status_codes
    assert "ALBUM" not in track_only.status_codes
    assert "ALBUM" in album_only.status_codes
    assert "TRACK" not in album_only.status_codes
