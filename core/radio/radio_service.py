"""# LEGACY — RadioService facade over the canonical core/radio/service.py.

Deprecated: this class exists only to keep the legacy QML-facing API
(add_station/get_stations/favorite_station/...) working while the canonical
implementation in :mod:`core.radio.service` owns all station, session and
history logic (ADR-002 single domain authority). New code must use
``core.radio.service.RadioService``. No parallel state lives here: every
operation delegates to a single canonical service instance.
"""
from __future__ import annotations

import logging
from math import ceil

from core.radio.repository import RadioRepository, RadioStation
from core.radio.models import (
    Station, PaginatedResult, StationCreateRequest, StationUpdateRequest,
)

logger = logging.getLogger("core.radio.radio_service")

try:  # pragma: no cover - exercised through the facade below
    from core.radio.service import RadioService as _CanonicalRadioService
except Exception:  # pragma: no cover
    _CanonicalRadioService = None


def _to_canonical_station(station: RadioStation) -> Station:
    return Station(
        id=station.id or station.url,
        name=station.name,
        stream_url=station.url,
        genre=station.genre,
        country=station.country,
        codec=station.codec,
        bitrate=station.bitrate,
        favorite=station.favorite,
        play_count=station.play_count,
    )


class _LegacyStationRepoAdapter:
    """Adapt the legacy in-memory :class:`RadioRepository` to the canonical
    repository interface so the facade can always delegate to the canonical
    service (kept for legacy tests; production uses the SQLite repos)."""

    def __init__(self, repo: RadioRepository):
        self._repo = repo

    def initialize(self):
        pass

    def add(self, req: StationCreateRequest) -> Station:
        result = self._repo.add_station(RadioStation(
            name=req.name, url=req.stream_url,
            genre=req.genre, country=req.country,
            codec=req.codec, bitrate=req.bitrate,
        ))
        station = self._repo.get_station(result["id"])
        return _to_canonical_station(station)

    def get(self, station_id) -> Station | None:
        station = self._repo.get_station(station_id)
        return _to_canonical_station(station) if station else None

    def update(self, station_id, req: StationUpdateRequest) -> Station | None:
        station = self._repo.get_station(station_id)
        if station is None:
            return None
        if req.name is not None:
            station.name = req.name
        if req.stream_url is not None:
            station.url = req.stream_url
        if req.genre is not None:
            station.genre = req.genre
        if req.country is not None:
            station.country = req.country
        if req.codec is not None:
            station.codec = req.codec
        if req.bitrate is not None:
            station.bitrate = req.bitrate
        return _to_canonical_station(station)

    def delete(self, station_id) -> bool:
        result = self._repo.remove_station(station_id)
        return bool(result.get("ok"))

    def set_favorite(self, station_id, favorite: bool) -> bool:
        station = self._repo.get_station(station_id)
        if station is None:
            return False
        if station.favorite != favorite:
            self._repo.toggle_favorite(station_id)
        return True

    def list_all(self, page: int = 1, page_size: int = 50,
                 sort_by: str = "name", sort_dir: str = "asc") -> PaginatedResult:
        stations = sorted(
            self._repo.get_all_stations(),
            key=lambda s: getattr(s, sort_by if sort_by in ("name", "genre", "country", "bitrate") else "name", ""),
            reverse=sort_dir == "desc",
        )
        return self._paginate([_to_canonical_station(s) for s in stations], page, page_size)

    def search(self, query: str, page: int = 1, page_size: int = 50) -> PaginatedResult:
        return self._paginate(
            [_to_canonical_station(s) for s in self._repo.search(query)],
            page, page_size,
        )

    def count(self) -> int:
        return len(self._repo.get_all_stations())

    def list_favorites(self, page: int = 1, page_size: int = 50) -> PaginatedResult:
        return self._paginate(
            [_to_canonical_station(s) for s in self._repo.get_favorites()],
            page, page_size,
        )

    def mark_played(self, station_id):
        # Only bump the station counters: the canonical service records the
        # history row separately through the history repository adapter.
        import time
        station = self._repo.get_station(station_id)
        if station is None:
            return
        station.last_played = time.time()
        station.play_count += 1

    def list_recent(self, limit: int = 20) -> list[Station]:
        stations = []
        for entry in self._repo.get_history(limit):
            station = self._repo.get_station(entry.get("station_id"))
            if station:
                stations.append(_to_canonical_station(station))
        return stations

    def get_all_for_export(self) -> list[Station]:
        return [_to_canonical_station(s) for s in self._repo.get_all_stations()]

    def update_probe(self, station_id, status: str, probe_at: str):
        pass

    def find_by_url(self, url: str) -> Station | None:
        for station in self._repo.get_all_stations():
            if station.url == url or station.id == url:
                return _to_canonical_station(station)
        return None

    def bulk_add(self, stations: list[StationCreateRequest], mode: str = "best_effort") -> int:
        count = 0
        for req in stations:
            result = self._repo.add_station(RadioStation(
                name=req.name, url=req.stream_url,
                genre=req.genre, country=req.country, codec=req.codec,
            ))
            if result.get("ok"):
                count += 1
        return count

    @staticmethod
    def _paginate(items: list[Station], page: int, page_size: int) -> PaginatedResult:
        total = len(items)
        start = (page - 1) * page_size
        return PaginatedResult(
            items=items[start:start + page_size],
            total=total, page=page, page_size=page_size,
            pages=max(1, ceil(total / page_size)) if total else 1,
        )


class _LegacyHistoryRepoAdapter:
    """Adapt legacy in-memory history (kept inside RadioRepository) to the
    canonical history repository interface."""

    def __init__(self, repo: RadioRepository):
        self._repo = repo

    def initialize(self):
        pass

    def record_play(self, station_id, title: str = "",
                    result: str = "played", error_code: str = ""):
        self._repo.record_play(station_id)

    def list_history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        entries = self._repo.get_history(limit + offset)
        return entries[offset:offset + limit]

    def clear_history(self, retention_days: int | None = None):
        self._repo.clear_history()

    def count_history(self) -> int:
        return len(self._repo.get_history())


class RadioService:
    """Deprecated thin facade over :class:`core.radio.service.RadioService`.

    .. deprecated::
        Use :class:`core.radio.service.RadioService` directly. This facade is
        kept for the legacy bridge/tests API during the ADR-002 migration.
    """

    def __init__(self, radio_manager=None, repository: RadioRepository | None = None,
                 event_bus=None):
        self._radio_manager = radio_manager
        self._event_bus = event_bus
        self._canonical: _CanonicalRadioService | None = None
        self._legacy_repo: RadioRepository | None = repository
        self._buffer_ms = 2000
        self._timeout_s = 10
        self._current_url = ""
        self._current_name = ""

    @property
    def repository(self):
        if self._legacy_repo is not None:
            return self._legacy_repo
        return None

    def _svc(self) -> _CanonicalRadioService:
        """Canonical service instance (single authority, built lazily)."""
        if self._canonical is None:
            if self._legacy_repo is not None:
                station_repo = _LegacyStationRepoAdapter(self._legacy_repo)
                history_repo = _LegacyHistoryRepoAdapter(self._legacy_repo)
            else:
                from core.paths import radio_database_path
                from infrastructure.radio.station_repository import SqliteStationRepository
                from infrastructure.radio.history_repository import SqliteRadioHistoryRepository

                station_repo = SqliteStationRepository(radio_database_path())
                history_repo = SqliteRadioHistoryRepository(radio_database_path())
                station_repo.initialize()
                history_repo.initialize()
            if _CanonicalRadioService is None:  # pragma: no cover
                raise RuntimeError("Canonical RadioService unavailable")
            self._canonical = _CanonicalRadioService(
                station_repo=station_repo,
                history_repo=history_repo,
                event_bus=self._event_bus,
            )
        return self._canonical

    def add_station(self, name: str, url: str, genre: str = "",
                    country: str = "", codec: str = "") -> dict:
        req = StationCreateRequest(
            name=name, stream_url=url, genre=genre,
            country=country, codec=codec,
        )
        result = self._svc().create_station(req)
        if result.ok and result.station:
            return {"ok": True, "id": result.station.id}
        return {"ok": False, "error": result.error.value or result.message}

    def edit_station(self, station_id: str, name: str = "", url: str = "",
                     genre: str = "", country: str = "", codec: str = "") -> dict:
        req = StationUpdateRequest(
            name=name or None, stream_url=url or None, genre=genre or None,
            country=country or None, codec=codec or None,
        )
        result = self._svc().update_station(station_id, req)
        return {"ok": result.ok, "error": result.error.value} if not result.ok else {"ok": True}

    def delete_station(self, station_id: str) -> dict:
        result = self._svc().delete_station(station_id)
        if not result.ok:
            return {"ok": False, "error": result.error.value}
        return {"ok": True}

    def get_stations(self, filter_text: str = "") -> list:
        if filter_text:
            result = self._svc().search_stations(filter_text)
        else:
            result = self._svc().list_stations(page_size=10000)
        return [self._station_dict(s) for s in result.items]

    def favorite_station(self, station_id: str) -> dict:
        result = self._svc().toggle_favorite(station_id)
        if not result.ok:
            return {"ok": False, "error": result.error.value}
        station = self._svc().get_station(station_id)
        if station.ok and station.station:
            return {"ok": True, "favorite": station.station.favorite}
        return {"ok": True}

    def get_favorites(self) -> list[dict]:
        result = self._svc().list_favorites(page_size=10000)
        return [{"id": s.id, "name": s.name, "url": s.stream_url} for s in result.items]

    def play_station(self, url: str, name: str = "") -> bool:
        for entry in self.get_stations():
            if entry["url"] == url or str(entry["id"]) == url:
                result = self._svc().start_station(entry["id"])
                if result.ok:
                    self._current_url = url
                    self._current_name = name or url
                return result.ok
        return False

    def stop(self) -> dict:
        self._current_url = ""
        self._svc().stop()
        return {"ok": True}

    def search_stations(self, query: str) -> dict:
        result = self._svc().search_stations(query, page_size=10000)
        return {"ok": True, "results": [self._station_dict(s) for s in result.items]}

    def import_stations(self, stations: list[dict]) -> dict:
        requests = [
            StationCreateRequest(
                name=s.get("name", "Unknown"),
                stream_url=s.get("url", ""),
                genre=s.get("genre", ""),
                country=s.get("country", ""),
                bitrate=s.get("bitrate", 0),
                codec=s.get("codec", ""),
            )
            for s in stations
        ]
        result = self._svc().bulk_import(requests)
        return {"ok": result.ok, "imported": result.details.get("imported", 0)}

    def export_stations(self) -> list[dict]:
        return self._svc().export_stations()

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._svc().history(limit=limit) or []

    def mark_played(self, station_id: str) -> dict:
        result = self._svc().mark_played(station_id)
        if not result.ok:
            return {"ok": False, "error": result.error.value}
        return {"ok": True}

    def clear_history(self) -> dict:
        self._svc().clear_history()
        return {"ok": True}

    def set_timeout_s(self, s: int):
        self._timeout_s = max(3, min(120, s))

    def set_buffer_ms(self, ms: int):
        self._buffer_ms = max(500, min(30000, ms))

    @staticmethod
    def _station_dict(station: Station) -> dict:
        return {
            "id": station.id,
            "name": station.name,
            "url": station.stream_url,
            "genre": station.genre,
            "country": station.country,
            "codec": station.codec,
            "bitrate": station.bitrate,
            "favorite": station.favorite,
        }
