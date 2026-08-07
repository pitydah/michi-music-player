"""D2: RADIO search domain routes through the canonical station repository.

The RADIO domain must never query a ``radio_stations`` table in the library
database (that table does not exist in production — radio persists in its own
SQLite database via ``SqliteStationRepository``). These tests exercise the
provider with a REAL repository over a temporary radio DB and verify honest
status codes: items on hits, OK on empty, SEARCH_FAILED only when the
repository is truly unavailable.
"""
from __future__ import annotations

from pathlib import Path

from core.global_search_service import GlobalSearchService
from core.radio.models import StationCreateRequest
from core.search.models import SEARCH_FAILED, STATUS_OK, SearchDomain, SearchRequest
from core.search.providers import (
    RadioStationSearchProvider,
    SearchProviderRegistry,
)
from infrastructure.radio.station_repository import SqliteStationRepository

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_SEARCH_DIR = PROJECT_ROOT / "core" / "search"


def _make_repo(db_path: str) -> SqliteStationRepository:
    repo = SqliteStationRepository(db_path)
    repo.initialize()
    return repo


def _make_svc(repo: SqliteStationRepository | None) -> GlobalSearchService:
    registry = SearchProviderRegistry()
    registry.register(SearchDomain.RADIO, RadioStationSearchProvider(repo))
    return GlobalSearchService(db_path="", provider_registry=registry)


def _search_radio(svc: GlobalSearchService, query: str):
    return svc.search_request(SearchRequest(
        query=query,
        domains=frozenset({SearchDomain.RADIO}),
        limit_per_domain=10, total_limit=50,
        owner="d2", request_id="d2",
    ))


def test_radio_domain_returns_stations(tmp_path) -> None:
    repo = _make_repo(str(tmp_path / "radio.db"))
    repo.bulk_add([
        StationCreateRequest(
            name="Rock FM", stream_url="http://rock.fm",
            genre="Rock", country="US", codec="MP3",
        ),
        StationCreateRequest(
            name="Jazz Corner", stream_url="http://jazz.fm",
            genre="Jazz", country="UK", codec="AAC",
        ),
        StationCreateRequest(
            name="Salsa Latina", stream_url="http://salsa.fm",
            genre="Latin", country="AR", codec="MP3",
        ),
    ])

    resp = _search_radio(_make_svc(repo), "rock")
    assert resp.error == ""
    assert SearchDomain.RADIO not in resp.domains_failed
    items = [i for i in resp.items if i.result_type == "radio"]
    assert len(items) == 1, "query 'rock' matches only Rock FM"
    item = items[0]
    assert item.title == "Rock FM"
    assert item.public_ref == f"radio_{item.result_id}"
    assert item.public_ref.startswith("radio_")
    assert item.extra["url"] == "http://rock.fm"
    assert item.extra["codec"] == "MP3"
    assert "US" in item.subtitle or "Rock" in item.subtitle
    assert resp.status_codes["RADIO"] == STATUS_OK


def test_radio_domain_matches_genre_and_country(tmp_path) -> None:
    repo = _make_repo(str(tmp_path / "radio.db"))
    repo.bulk_add([
        StationCreateRequest(
            name="Jazz Corner", stream_url="http://jazz.fm",
            genre="Jazz", country="UK", codec="AAC",
        ),
        StationCreateRequest(
            name="Salsa Latina", stream_url="http://salsa.fm",
            genre="Latin", country="AR", codec="MP3",
        ),
    ])

    resp = _search_radio(_make_svc(repo), "latin")
    items = [i for i in resp.items if i.result_type == "radio"]
    assert [i.title for i in items] == ["Salsa Latina"]

    resp = _search_radio(_make_svc(repo), "uk")
    items = [i for i in resp.items if i.result_type == "radio"]
    assert [i.title for i in items] == ["Jazz Corner"]


def test_radio_domain_empty(tmp_path) -> None:
    repo = _make_repo(str(tmp_path / "radio.db"))

    resp = _search_radio(_make_svc(repo), "rock")
    assert resp.items == []
    assert SearchDomain.RADIO not in resp.domains_failed
    assert resp.status_codes["RADIO"] == STATUS_OK, (
        "an empty radio DB is a healthy OK, never SEARCH_FAILED"
    )
    assert resp.status_codes["RADIO"] != SEARCH_FAILED


def test_radio_domain_repo_unavailable() -> None:
    resp = _search_radio(_make_svc(None), "rock")
    assert resp.items == []
    assert SearchDomain.RADIO in resp.domains_failed
    assert resp.status_codes["RADIO"] == SEARCH_FAILED, (
        "missing repository is a real error: honest SEARCH_FAILED, no crash"
    )


def test_radio_domain_no_library_table_dependency() -> None:
    """Source scan: core/search never references the library radio_stations
    table — the table does not exist in the production library schema."""
    assert CORE_SEARCH_DIR.is_dir()
    for path in sorted(CORE_SEARCH_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "radio_stations" not in source, (
            f"{path.relative_to(PROJECT_ROOT)} must not query the library "
            "radio_stations table"
        )
