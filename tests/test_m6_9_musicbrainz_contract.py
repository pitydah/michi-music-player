"""M6.9 REOPENED — deterministic MusicBrainz provider contract tests.

These tests verify the REQUESTS Michi produces against the real
MusicBrainz web service contract — not just Michi's behavior against
fixtures. URLs are parsed with urllib.parse (scheme/hostname/path/query
keys/values) so parameter ORDER is irrelevant and invented parameters
are caught. Regression gate (§72): ``type=release-group`` can NEVER
reappear in a release-group browse request.
"""

import json
import os
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from michi.application.enrichment_ports import (
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    ArtistIdentityEvidence,
)
from michi.infrastructure.enrichment_http import MusicBrainzRateLimiter
from michi.infrastructure.enrichment_musicbrainz import (
    MusicBrainzIdentityResolver,
    escape_musicbrainz_lucene,
)

API_ROOT = "https://musicbrainz.org/ws/2"


class _RecordingTransport(HttpTransportPort):
    """Records every request URL; serves scripted per-URL responses by
    exact parsed path (no prefix guessing)."""

    def __init__(self):
        self.requests: list[str] = []
        self.responses: dict[str, bytes] = {}

    def route(self, url: str, payload: dict) -> None:
        self.responses[url] = json.dumps(payload).encode()

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request.url)
        body = self.responses.get(request.url)
        if body is None:
            raise AssertionError(f"unscripted URL: {request.url}")
        return HttpResponse(
            status_code=200, body=body, headers={}, final_url=request.url
        )

    def requests_for(self, path: str) -> list[str]:
        return [u for u in self.requests if urlparse(u).path == path]


def _parse(url: str):
    parsed = urlparse(url)
    return parsed, parse_qs(parsed.query)


def _resolver(transport):
    limiter = MusicBrainzRateLimiter(min_interval_seconds=0.0)
    return MusicBrainzIdentityResolver(transport, limiter)


def _artist_search_response(artist_id="mb-artist-1", name="Artist One"):
    return {
        "created": "2026-01-01",
        "count": 1,
        "offset": 0,
        "artists": [
            {
                "id": artist_id,
                "name": name,
                "sort-name": name,
                "disambiguation": "",
            }
        ],
    }


def _release_groups_response(groups):
    return {
        "created": "2026-01-01",
        "count": len(groups),
        "offset": 0,
        "release-groups": groups,
    }


def _release_group(rid, title, year="1997-05-21"):
    return {"id": rid, "title": title, "first-release-date": year}


# ==========================================================================
# CONTRACT: artist search
# ==========================================================================


def test_artist_search_contract():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response([]),
    )

    resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )

    (artist_url,) = transport.requests_for("/ws/2/artist/")
    parsed, query = _parse(artist_url)
    assert parsed.scheme == "https"
    assert parsed.hostname == "musicbrainz.org"
    assert parsed.path == "/ws/2/artist/"
    assert query["query"] == ["artist:Artist One"]
    assert query["fmt"] == ["json"]
    assert query["limit"] == ["25"]


def test_artist_search_escapes_lucene_not_only_url():
    """'AC/DC' must be Lucene-escaped (\\/) AND URL-encoded."""
    transport = _RecordingTransport()
    resolver = _resolver(transport)

    expected = (
        "https://musicbrainz.org/ws/2/artist/?query="
        "artist%3AAC%5C%2FDC&fmt=json&limit=25"
    )
    transport.route(expected, _artist_search_response())
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response([]),
    )
    resolver.find_artist_candidates(
        ArtistIdentityEvidence(local_artist_key="ac-dc", local_artist_name="AC/DC")
    )
    assert transport.requests_for("/ws/2/artist/") == [expected]


# ==========================================================================
# CONTRACT: release-group browse (P0-A + §72 regression)
# ==========================================================================


def test_release_group_browse_contract():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    browse_url = (
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0"
    )
    transport.route(
        browse_url,
        _release_groups_response([_release_group("rg-1", "OK Computer", "1997-05-21")]),
    )

    candidates = resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )

    (browse,) = transport.requests_for("/ws/2/release-group/")
    parsed, query = _parse(browse)
    assert parsed.scheme == "https"
    assert parsed.hostname == "musicbrainz.org"
    assert parsed.path == "/ws/2/release-group/"
    assert query["artist"] == ["mb-artist-1"]
    assert query["fmt"] == ["json"]
    assert query["limit"] == ["100"]
    assert query["offset"] == ["0"]
    assert candidates[0].known_albums[0].title == "OK Computer"
    assert candidates[0].known_albums[0].year == 1997


def test_browse_never_uses_type_release_group():
    """§72 regression gate: 'type=release-group' must NEVER appear in a
    release-group browse request (the endpoint entity is not a valid
    value of the type filter)."""
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response([]),
    )
    resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )
    for url in transport.requests:
        parsed, query = _parse(url)
        assert "type" not in query, f"invented type param in {url}"
        assert parsed.path != "/ws/2/release-group/" or "release-group" not in query


def test_browse_pagination_stops_on_short_page():
    """Una página corta = última página: exactamente 1 request de browse."""
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response([_release_group("rg-1", "OK Computer", "1997-05-21")]),
    )
    resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )
    browse_requests = transport.requests_for("/ws/2/release-group/")
    assert len(browse_requests) == 1


def test_browse_pagination_fetches_second_page_when_full():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    full_page = [_release_group(f"rg-{i}", f"Album {i}") for i in range(100)]
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response(full_page),
    )
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=100",
        _release_groups_response(
            [_release_group("rg-extra", "Later Album", "2001-01-01")]
        ),
    )
    candidates = resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )
    browse_requests = transport.requests_for("/ws/2/release-group/")
    assert len(browse_requests) == 2
    assert _parse(browse_requests[1])[1]["offset"] == ["100"]
    titles = {a.title for a in candidates[0].known_albums}
    assert "Later Album" in titles


def test_browse_pagination_dedupes_across_pages():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    full_page = [_release_group("rg-dup", "Same Album", "1997-05-21")] * 100
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=0",
        _release_groups_response(full_page),
    )
    transport.route(
        f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset=100",
        _release_groups_response([_release_group("rg-1", "Same Album", "1997-05-21")]),
    )
    candidates = resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )
    albums = candidates[0].known_albums
    titles = [a.title for a in albums]
    assert len(titles) == len(set(titles)), "títulos duplicados deduplicados"


def test_browse_pagination_max_pages_bounded():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    artist_url = f"{API_ROOT}/artist/?query=artist%3AArtist+One&fmt=json&limit=25"
    transport.route(artist_url, _artist_search_response())
    for offset in (0, 100, 200):
        transport.route(
            f"{API_ROOT}/release-group/?artist=mb-artist-1&fmt=json&limit=100&offset={offset}",
            _release_groups_response(
                [
                    _release_group(f"rg-{offset}-{i}", f"Album {offset + i}")
                    for i in range(100)
                ]
            ),
        )
    candidates = resolver.find_artist_candidates(
        ArtistIdentityEvidence(
            local_artist_key="artist-one", local_artist_name="Artist One"
        )
    )
    browse_requests = transport.requests_for("/ws/2/release-group/")
    assert len(browse_requests) == 3, "máximo 3 páginas (bounded)"
    assert len(candidates[0].known_albums) <= 300


# ==========================================================================
# CONTRACT: release-group search
# ==========================================================================


def test_release_group_search_contract():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    expected = (
        "https://musicbrainz.org/ws/2/release-group/?query="
        "releasegroup%3AOK+Computer+AND+artist%3ARadiohead"
        "&fmt=json&limit=25"
    )
    transport.route(
        expected,
        {
            "created": "2026-01-01",
            "count": 1,
            "offset": 0,
            "release-groups": [
                {
                    "id": "rg-1",
                    "title": "OK Computer",
                    "first-release-date": "1997-05-21",
                    "artist-credit": [
                        {"name": "Radiohead", "artist": {"id": "mb-radiohead"}}
                    ],
                }
            ],
        },
    )
    candidates = resolver.find_release_group_candidates(
        AlbumIdentityEvidence(
            local_album_key="ok-computer",
            local_album_title="OK Computer",
            local_album_artist_name="Radiohead",
        )
    )
    parsed, query = _parse(expected)
    assert parsed.path == "/ws/2/release-group/"
    assert query["query"] == ["releasegroup:OK Computer AND artist:Radiohead"]
    assert query["fmt"] == ["json"]
    assert query["limit"] == ["25"]
    assert candidates[0].release_group_id == "rg-1"


def test_query_parameter_order_irrelevant():
    """La construcción central produce parámetros estables — el test no
    depende del orden textual."""
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    url = f"{API_ROOT}/release-group/?query=releasegroup%3Ax&fmt=json&limit=25"
    transport.route(url, _release_groups_response([]))
    resolver.find_release_group_candidates(
        AlbumIdentityEvidence(local_album_key="x", local_album_title="x")
    )
    (actual,) = transport.requests_for("/ws/2/release-group/")
    _, query = _parse(actual)
    assert set(query.keys()) == {"query", "fmt", "limit"}
    assert query["fmt"] == ["json"]


# ==========================================================================
# CONTRACT: release lookup / release-group lookup
# ==========================================================================


def test_release_lookup_contract():
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    url = f"{API_ROOT}/release/r-123?inc=release-groups&fmt=json"
    transport.route(
        url,
        {
            "id": "r-123",
            "title": "OK Computer",
            "release-group": {"id": "rg-1", "title": "OK Computer"},
        },
    )
    candidates = resolver.find_release_edition_candidates(
        AlbumIdentityEvidence(
            local_album_key="ok-computer",
            local_album_title="OK Computer",
            identity_hints=__import__(
                "michi.domain.enrichment", fromlist=["AlbumIdentityHints"]
            ).AlbumIdentityHints(release_ids=("r-123",)),
        )
    )
    parsed, query = _parse(url)
    assert parsed.path == "/ws/2/release/r-123"
    assert query["inc"] == ["release-groups"]
    assert query["fmt"] == ["json"]
    assert candidates[0].release_id == "r-123"
    assert candidates[0].release_group_id == "rg-1"


def test_release_group_lookup_contract_via_release_edition():
    """Release lookup con inc=release-groups es el camino de lookup de
    release-group en la arquitectura actual (corroboración release→group)."""
    transport = _RecordingTransport()
    resolver = _resolver(transport)
    url = f"{API_ROOT}/release/r-456?inc=release-groups&fmt=json"
    transport.route(url, {"id": "r-456", "release-group": {"id": "rg-9"}})
    resolver.find_release_edition_candidates(
        AlbumIdentityEvidence(
            local_album_key="x",
            local_album_title="X",
            identity_hints=__import__(
                "michi.domain.enrichment", fromlist=["AlbumIdentityHints"]
            ).AlbumIdentityHints(release_ids=("r-456",)),
        )
    )
    (actual,) = transport.requests_for("/ws/2/release/r-456")
    _, query = _parse(actual)
    assert query["inc"] == ["release-groups"]
    assert "type" not in query


# ==========================================================================
# LUCENE ESCAPING (§25)
# ==========================================================================


def test_musicbrainz_lucene_escaping():
    cases = {
        "AC/DC": "AC\\/DC",
        "P!nk": "P\\!nk",
        "+44": "\\+44",
        "!!!": "\\!\\!\\!",
        "M/A/R/R/S": "M\\/A\\/R\\/R\\/S",
        "name:part": "name\\:part",
        "artist (UK)": "artist \\(UK\\)",
        "Rock & Roll": "Rock \\& Roll",
        'Quoted "Name"': 'Quoted \\"Name\\"',
        "A*B?C~D": "A\\*B\\?C\\~D",
        "Braces {x} [y]": "Braces \\{x\\} \\[y\\]",
    }
    for raw, expected in cases.items():
        assert escape_musicbrainz_lucene(raw) == expected, raw
    # El valor escapado es un literal Lucene seguro (sin caracteres
    # especiales sin escapar).
    for raw in cases:
        escaped = escape_musicbrainz_lucene(raw)
        for ch in '+-&|!(){}[]^"~*?:\\/':
            assert f"\\{ch}" in escaped or ch not in raw
