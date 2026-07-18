"""RadioService — radio playback and station management."""
from __future__ import annotations

import logging
from typing import Any

from core.radio.repository import RadioRepository, RadioStation

logger = logging.getLogger("core.radio.radio_service")


class RadioService:
    def __init__(self, radio_manager=None, repository: RadioRepository | None = None,
                 event_bus=None):
        self._radio_manager = radio_manager
        self._repo = repository or RadioRepository()
        self._event_bus = event_bus
        self._buffer_ms = 2000
        self._timeout_s = 10
        self._current_url = ""
        self._current_name = ""

    @property
    def repository(self) -> RadioRepository:
        return self._repo

    def add_station(self, name: str, url: str, genre: str = "",
                    country: str = "") -> dict:
        station = RadioStation(name=name, url=url, genre=genre, country=country)
        return self._repo.add_station(station)

    def edit_station(self, station_id: str, name: str = "", url: str = "",
                     genre: str = "") -> dict:
        station = self._repo.get_station(station_id)
        if not station:
            return {"ok": False, "error": "NOT_FOUND"}
        if name:
            station.name = name
        if url:
            station.url = url
        if genre:
            station.genre = genre
        return {"ok": True}

    def delete_station(self, station_id: str) -> dict:
        return self._repo.remove_station(station_id)

    def get_stations(self, filter_text: str = "") -> list:
        if filter_text:
            return [{"id": s.id or s.url, "name": s.name, "url": s.url,
                     "genre": s.genre, "bitrate": s.bitrate, "favorite": s.favorite}
                    for s in self._repo.search(filter_text)]
        return [{"id": s.id or s.url, "name": s.name, "url": s.url,
                 "genre": s.genre, "bitrate": s.bitrate, "favorite": s.favorite}
                for s in self._repo.get_all_stations()]

    def favorite_station(self, station_id: str) -> dict:
        return self._repo.toggle_favorite(station_id)

    def get_favorites(self) -> list[dict]:
        return [{"id": s.id or s.url, "name": s.name, "url": s.url} for s in self._repo.get_favorites()]

    def play_station(self, url: str, name: str = "") -> bool:
        self._current_url = url
        self._current_name = name or url
        if self._radio_manager:
            result = self._radio_manager.play(url, self._current_name)
            if result:
                for s in self._repo.get_all_stations():
                    if s.url == url or s.id == url:
                        self._repo.record_play(s.id or url)
                        break
            return result
        return False

    def stop(self) -> dict:
        self._current_url = ""
        if self._radio_manager and hasattr(self._radio_manager, 'stop'):
            self._radio_manager.stop()
            return {"ok": True}
        return {"ok": True}

    def search_stations(self, query: str) -> dict:
        results = self._repo.search(query)
        return {"ok": True, "results": [{"id": s.id or s.url, "name": s.name,
                                          "url": s.url, "genre": s.genre}
                                         for s in results]}

    def import_stations(self, stations: list[dict]) -> dict:
        return self._repo.import_stations(stations)

    def export_stations(self) -> list[dict]:
        return [{"name": s.name, "url": s.url, "genre": s.genre}
                for s in self._repo.get_all_stations()]

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._repo.get_history(limit)

    def clear_history(self) -> dict:
        return self._repo.clear_history()

    def set_timeout_s(self, s: int):
        self._timeout_s = max(3, min(120, s))

    def set_buffer_ms(self, ms: int):
        self._buffer_ms = max(500, min(30000, ms))
